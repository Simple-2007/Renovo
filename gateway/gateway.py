"""Renovo — шлюз между Arduino UNO и сервером.

Читает COM-порт контроллера и отправляет замеры в API сайта.

    python gateway.py                 порт определяется автоматически
    python gateway.py --port COM4     явное указание порта
    python gateway.py --list          показать доступные порты и выйти

Настройки берутся из файла .env рядом со скриптом (см. .env.example)
и могут быть переопределены аргументами командной строки.

Поддерживаются два формата строк от контроллера, определяются автоматически:

  1. WeatherStation (прошивка на 9600 бод):
         DATA;<номер>;<ГГГГ-ММ-ДД ЧЧ:ММ:СС>;t1;t2;t3;t4;t5
     ВАЖНО: эта прошивка выводит замеры в порт только пока считает, что ПК на
     связи, а флаг взводится исключительно командой PING. Поэтому шлюз обязан
     периодически пинговать плату — иначе записи уйдут на SD-карту (а при её
     отсутствии просто пропадут).

  2. renovo_temp (прошивка на 115200 бод):
         {"boot":...,"seq":...,"age":0,"t":{"s1":23.5,...}}

Накопление данных при обрыве связи здесь пока не реализовано: при недоступном
сервере пакет логируется и теряется. Место, куда встанет буфер, отмечено
комментарием в send_packet().
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
import time
from pathlib import Path

try:
    import requests
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("Не установлены зависимости. Выполните: pip install -r requirements.txt")

def app_dir() -> Path:
    """Каталог рядом с программой.

    У собранного PyInstaller onefile-приложения __file__ указывает во временную
    папку распаковки, поэтому .env нужно искать рядом с самим .exe.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


try:
    from dotenv import load_dotenv
    load_dotenv(app_dir() / ".env")
except ImportError:
    pass

log = logging.getLogger("gateway")

# Признаки USB-переходников, которые ставят на UNO и её клоны.
PORT_HINTS = ("arduino", "ch340", "ch341", "usb-serial", "usb serial", "wch", "ft232", "cp210")

RECONNECT_DELAY = 3.0      # пауза перед повторным открытием порта, сек
HTTP_RETRY_DELAY = 2.0     # пауза после сетевой ошибки, сек
PING_INTERVAL = 10.0       # как часто пинговать плату, сек

INVALID_TEMP = -99.0       # чем прошивка помечает «значения нет»
MIN_VALID_YEAR = 2020      # метки времени старше считаем сбоем часов

# Служебные ответы прошивки — их полезно видеть в логе.
STATUS_PREFIXES = ("PONG", "STATUS;", "TIME_OK", "RTC_ERROR", "RTC_LOST",
                   "BUFFER_EMPTY", "BUFFER_ERROR", "BUFFER_FINISHED")


def find_port() -> str | None:
    """Ищет порт контроллера среди доступных COM-портов."""
    ports = list(list_ports.comports())
    if not ports:
        return None
    for port in ports:
        haystack = f"{port.description} {port.manufacturer or ''}".lower()
        if any(hint in haystack for hint in PORT_HINTS):
            log.info("Найден контроллер: %s (%s)", port.device, port.description)
            return port.device
    if len(ports) == 1:
        log.info("Единственный доступный порт: %s (%s)", ports[0].device, ports[0].description)
        return ports[0].device
    log.warning("Не удалось определить порт автоматически. Доступны: %s",
                ", ".join(p.device for p in ports))
    return None


def print_ports() -> None:
    ports = list(list_ports.comports())
    if not ports:
        print("COM-портов не найдено.")
        return
    print("Доступные порты:")
    for port in ports:
        print(f"  {port.device:<8} {port.description}")


class ClockState:
    """Помнит, жаловались ли уже на часы контроллера.

    Без DS3231 прошивка отдаёт что-то вроде 2000-01-01 в каждой строке.
    Ругаться на это каждые три минуты бессмысленно, поэтому предупреждаем
    один раз и переключаемся на время сервера; когда модуль появится,
    так же однократно сообщим, что метки снова свои.
    """

    def __init__(self) -> None:
        self.warned = False
        self.using_device_time = False


def parse_data_line(line: str, clock: ClockState) -> dict | None:
    """Разбирает строку прошивки WeatherStation в пакет для API."""
    # При выгрузке буфера прошивка печатает «DATA;» перед строкой, которая
    # уже начинается с «DATA;», — снимаем префикс столько раз, сколько нужно.
    body = line
    while body.startswith("DATA;"):
        body = body[len("DATA;"):]

    parts = [p.strip() for p in body.split(";")]
    if len(parts) < 3:
        log.debug("Строка DATA слишком короткая, пропущена: %.80s", line)
        return None

    try:
        number = int(parts[0])
    except ValueError:
        log.debug("Не разобран номер записи: %.80s", line)
        return None

    temps: dict[str, float] = {}
    for index, raw in enumerate(parts[2:], start=1):
        try:
            value = float(raw)
        except ValueError:
            continue
        # Прошивка ставит -99 там, где ни одного годного показания не было.
        if value <= INVALID_TEMP:
            continue
        temps[f"s{index}"] = value

    if not temps:
        log.warning("Запись %s без единого исправного датчика, пропущена", number)
        return None

    packet: dict = {"seq": number, "t": temps}

    # Метка времени контроллера: используем, только если часы похожи на живые.
    stamp = parts[1]
    try:
        parsed = dt.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        parsed = None

    if parsed and parsed.year >= MIN_VALID_YEAR:
        if not clock.using_device_time:
            log.info("Часы контроллера в порядке, время берём с них")
            clock.using_device_time = True
        # Часы контроллера идут по местному времени — переводим в UTC,
        # добавляя смещение часового пояса этого компьютера.
        packet["ts"] = parsed.astimezone().isoformat()
    else:
        if not clock.warned:
            log.warning("Часы контроллера отдают '%s' — модуль DS3231 не найден или сбит. "
                        "Время замеров будет ставить сервер.", stamp)
            clock.warned = True
        clock.using_device_time = False
        packet["age"] = 0

    return packet


def check_connection(url: str, key: str, timeout: float) -> int:
    """Проверяет доступность сервера и правильность ключа. Ничего не записывает."""
    whoami = url.rsplit("/", 1)[0] + "/whoami"
    log.info("Проверяю %s", whoami)
    try:
        response = requests.get(whoami, headers={"X-Device-Key": key}, timeout=timeout)
    except requests.RequestException as exc:
        log.error("Сервер недоступен: %s", exc)
        return 1

    if response.status_code == 401:
        log.error("Ключ устройства не принят. Проверьте DEVICE_KEY в .env")
        return 1
    if not response.ok:
        log.error("Сервер ответил %s: %s", response.status_code, response.text[:300])
        return 1

    data = response.json()
    device = data["device"]
    log.info("Связь с сервером есть.")
    log.info("  устройство:      %s (%s)", device["name"], device["slug"])
    log.info("  датчики:         %s", ", ".join(data["sensors"]) or "ещё не заведены")
    log.info("  замеров в базе:  %s", data["readings_total"])
    log.info("  последняя связь: %s", device["last_seen"] or "данных ещё не было")
    return 0


def send_packet(session: requests.Session, url: str, key: str, packet: dict, timeout: float) -> bool:
    """Отправляет один пакет на сервер. Возвращает True при успешной записи."""
    try:
        response = session.post(url, json=packet, headers={"X-Device-Key": key}, timeout=timeout)
    except requests.RequestException as exc:
        # СЮДА встанет запись в буфер, когда будем делать накопление:
        # пакет не доставлен, его нужно сохранить до восстановления связи.
        log.warning("Сеть недоступна (запись %s): %s", packet.get("seq"), exc)
        return False

    if response.status_code == 401:
        log.error("Сервер не принял ключ устройства. Проверьте DEVICE_KEY в .env")
        return False
    if not response.ok:
        log.warning("Сервер ответил %s: %s", response.status_code, response.text[:300])
        return False

    data = response.json()
    if data.get("skipped"):
        log.warning("Сервер отбросил сбойные датчики: %s", ", ".join(data["skipped"]))
    log.info("запись %s принята, датчиков: %s", data.get("ack"), data.get("received"))
    return True


def handle_line(line: str, clock: ClockState, session, url, key, timeout, dry_run: bool = False) -> None:
    """Разбирает одну строку от контроллера и при необходимости шлёт её на сервер."""
    if dry_run:
        log.info("ПОЛУЧЕНО: %s", line)
    if line.startswith("#"):
        log.debug("контроллер: %s", line.lstrip("# "))
        return

    if line.startswith(STATUS_PREFIXES):
        log.debug("контроллер: %s", line)
        if line.startswith(("RTC_ERROR", "RTC_LOST")):
            log.warning("Контроллер сообщает о проблеме с часами: %s", line)
        return

    packet = None
    if line.startswith("DATA;"):
        packet = parse_data_line(line, clock)
    elif line.startswith("{"):
        try:
            packet = json.loads(line)
        except json.JSONDecodeError:
            log.debug("Строка не является JSON, пропущена: %.80s", line)
    else:
        log.debug("Неопознанная строка, пропущена: %.80s", line)

    if not packet:
        return

    if dry_run:
        log.info("РАЗОБРАНО: %s", json.dumps(packet, ensure_ascii=False))
        log.info("(проверочный режим — на сервер не отправлено)")
        return

    if not send_packet(session, url, key, packet, timeout):
        time.sleep(HTTP_RETRY_DELAY)


def run(port_name: str | None, baud: int, url: str, key: str, timeout: float,
        sync_rtc: bool, dry_run: bool = False, reset_board: bool = False) -> None:
    session = requests.Session()
    if dry_run:
        log.info("Проверочный режим: читаю порт и показываю данные, "
                 "на сервер ничего не отправляю. Остановка — Ctrl+C.")
    clock = ClockState()

    while True:
        target = port_name or find_port()
        if not target:
            log.error("Контроллер не найден, повтор через %.0f с", RECONNECT_DELAY)
            time.sleep(RECONNECT_DELAY)
            continue

        conn = serial.Serial()
        conn.port = target
        conn.baudrate = baud
        # timeout на чтение нужен, чтобы успевать слать PING и ловить Ctrl+C.
        conn.timeout = 1
        if not reset_board:
            # Не дёргаем DTR/RTS при открытии порта. На UNO это вызывает
            # перезагрузку платы, а с ней обнуляется таймер замеров: при
            # нестабильном USB плата не доживает до первого замера и данные
            # не появляются вообще.
            conn.dtr = False
            conn.rts = False

        try:
            conn.open()
            log.info("Порт %s открыт на %d бод%s", target, baud,
                     "" if reset_board else " (без перезагрузки платы)")
            if reset_board:
                time.sleep(2)   # ждём загрузки скетча после сброса
            conn.reset_input_buffer()

            if sync_rtc:
                # Формат разбирается прошивкой по фиксированным позициям,
                # поэтому менять его нельзя.
                stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.write(f"TIME;{stamp}\n".encode())
                log.info("Отправлена установка часов: %s", stamp)

            last_ping = 0.0
            while True:
                now = time.monotonic()
                if now - last_ping >= PING_INTERVAL:
                    # Без этого прошивка WeatherStation считает, что ПК нет,
                    # и не выводит замеры в порт вообще.
                    conn.write(b"PING\n")
                    last_ping = now

                raw = conn.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if line:
                    handle_line(line, clock, session, url, key, timeout, dry_run)

        except serial.SerialException as exc:
            log.error("Порт потерян (%s), переподключение через %.0f с", exc, RECONNECT_DELAY)
            time.sleep(RECONNECT_DELAY)
        except KeyboardInterrupt:
            log.info("Остановлено пользователем")
            return
        finally:
            try:
                conn.close()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Шлюз Arduino UNO -> сайт Renovo")
    parser.add_argument("--port", default=os.getenv("SERIAL_PORT") or None,
                        help="COM-порт контроллера, напр. COM4 (по умолчанию — автоопределение)")
    parser.add_argument("--baud", type=int, default=int(os.getenv("BAUD", "9600")),
                        help="скорость порта: 9600 для WeatherStation, 115200 для renovo_temp")
    parser.add_argument("--url", default=os.getenv("API_URL", "https://renovo.leikom.ru/api/v1/readings"),
                        help="адрес приёмника на сервере")
    parser.add_argument("--key", default=os.getenv("DEVICE_KEY", ""),
                        help="ключ устройства из админки")
    parser.add_argument("--timeout", type=float, default=float(os.getenv("HTTP_TIMEOUT", "10")),
                        help="таймаут HTTP-запроса, сек")
    parser.add_argument("--no-rtc-sync", action="store_true",
                        default=os.getenv("SYNC_RTC", "1") == "0",
                        help="не отправлять команду установки часов при подключении")
    parser.add_argument("--list", action="store_true", help="показать доступные COM-порты и выйти")
    parser.add_argument("--check", action="store_true",
                        help="проверить связь с сервером и ключ устройства, не читая порт")
    parser.add_argument("--dry-run", action="store_true",
                        help="читать порт и показывать данные, ничего не отправляя на сервер")
    parser.add_argument("--reset-board", action="store_true",
                        help="перезагружать плату при открытии порта (по умолчанию нет: "
                             "перезагрузка обнуляет таймер замеров прошивки)")
    parser.add_argument("--debug", action="store_true", help="подробный лог")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.list:
        print_ports()
        return

    # В проверочном режиме ключ не нужен: на сервер мы не ходим.
    if not args.key and not args.dry_run:
        sys.exit("Не задан ключ устройства. Пропишите DEVICE_KEY в .env или передайте --key")

    if args.check:
        sys.exit(check_connection(args.url, args.key, args.timeout))

    if not args.dry_run:
        log.info("Приёмник: %s", args.url)
    run(args.port, args.baud, args.url, args.key, args.timeout,
        not args.no_rtc_sync, args.dry_run, args.reset_board)


if __name__ == "__main__":
    main()
