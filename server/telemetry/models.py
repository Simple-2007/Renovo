import hashlib
import secrets
from zoneinfo import ZoneInfo, available_timezones

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Число слотов в категориальной палитре. Цвета живут в CSS (свои для светлой
# и тёмной темы), сюда приходит только номер слота: датчик получает его один
# раз при заведении и больше не меняет, поэтому выключение серии на графике
# никого не перекрашивает.
SERIES_SLOTS = 8


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """Отпечаток ключа для хранения в базе.

    Соль не нужна и только мешала бы: ключ выдаём сами, он случайный на
    256 бит, перебирать такой бессмысленно. Зато без соли отпечаток можно
    искать по индексу, а не сверять перебором со всеми устройствами.
    """
    return hashlib.sha256(key.strip().encode()).hexdigest()


class Device(models.Model):
    """Контроллер-источник данных (Arduino UNO через шлюз на ПК)."""

    name = models.CharField("название", max_length=100)
    slug = models.SlugField("код", max_length=50, unique=True)
    # Самого ключа в базе нет: он показывается один раз при выпуске, дальше
    # хранится только его отпечаток. Утечка дампа базы не даёт возможности
    # слать замеры от имени устройства.
    api_key_hash = models.CharField("отпечаток ключа", max_length=64, unique=True, editable=False)
    api_key_prefix = models.CharField(
        "начало ключа", max_length=12, blank=True, editable=False,
        help_text="Первые символы — чтобы узнать ключ, не показывая его целиком.",
    )
    api_key_issued_at = models.DateTimeField("ключ выпущен", null=True, blank=True, editable=False)
    is_active = models.BooleanField("активно", default=True)
    # Пояс места, где стоят датчики. Время на сайте показывается именно в нём,
    # а не в поясе того, кто смотрит: смысл имеет связь температуры с местным
    # временем суток на площадке, а не с часами наблюдателя.
    site_timezone = models.CharField(
        "часовой пояс площадки", max_length=64, default="Europe/Rome",
        help_text="Где физически стоят датчики. Например Europe/Rome для Сардинии, "
                  "Asia/Krasnoyarsk для Красноярска.",
    )
    report_interval_sec = models.PositiveIntegerField(
        "интервал замеров, с", default=180,
        help_text="Как часто контроллер шлёт данные. По нему считается, "
                  "потеряна ли связь, и когда показания на сайте считать несвежими.",
    )
    last_seen_at = models.DateTimeField("последняя связь", null=True, blank=True)
    created_at = models.DateTimeField("создано", auto_now_add=True)

    class Meta:
        verbose_name = "устройство"
        verbose_name_plural = "устройства"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def issue_api_key(self) -> str:
        """Выдаёт новый ключ и запоминает только его отпечаток.

        Возвращённую строку показывают владельцу один раз — восстановить её
        потом неоткуда. Старый ключ перестаёт работать сразу же: сверяется
        отпечаток, а он уже другой.
        """
        key = generate_api_key()
        self.api_key_hash = hash_api_key(key)
        self.api_key_prefix = key[:8]
        self.api_key_issued_at = timezone.now()
        return key

    def clean(self):
        if self.site_timezone not in available_timezones():
            raise ValidationError({
                "site_timezone": f"Неизвестный часовой пояс: {self.site_timezone}. "
                                 f"Нужно имя вида Europe/Rome."
            })

    @property
    def tzinfo(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.site_timezone)
        except Exception:
            return ZoneInfo("UTC")

    @property
    def offline_after_sec(self) -> float:
        """Сколько ждать данных, прежде чем считать связь потерянной.

        Отсчитывается от интервала замеров, а не от фиксированной минуты:
        контроллер с трёхминутным циклом иначе всегда числился бы офлайн.
        """
        return self.report_interval_sec * 2.5

    @property
    def is_online(self) -> bool:
        if not self.last_seen_at:
            return False
        return (timezone.now() - self.last_seen_at).total_seconds() < self.offline_after_sec


class Sensor(models.Model):
    """Датчик на устройстве.

    Заводится автоматически при первом замере с новым ключом, поэтому
    добавление шестого, десятого и любого следующего датчика не требует
    ни миграций, ни правок кода — достаточно начать слать его в пакете.
    """

    device = models.ForeignKey(
        Device, verbose_name="устройство", on_delete=models.CASCADE, related_name="sensors"
    )
    key = models.CharField("ключ", max_length=32, help_text="Идентификатор в пакете от контроллера, напр. s1")
    label = models.CharField("название", max_length=100, blank=True, help_text="Понятное имя, напр. Цех 1 / вход")
    unit = models.CharField("единица", max_length=16, default="°C")
    color = models.CharField(
        "цвет на графике", max_length=7, blank=True,
        help_text="Оставьте пустым — цвет назначится по палитре. HEX вида #2a78d6 переопределит его.",
    )
    order = models.PositiveIntegerField("порядок", default=0)
    # Слот палитры закреплён за датчиком, а не за его местом в списке:
    # иначе перестановка карточек перекрашивала бы линии на графике, и
    # «синий» переставал бы означать один и тот же датчик.
    slot = models.PositiveSmallIntegerField("слот палитры", default=1, editable=False)
    # Пороги подкраски значения на карточке. Ниже warn_above число набрано
    # обычным цветом; от warn_above к alarm_above оно плавно уходит в красный.
    # Пустые поля отключают подкраску: цвет без порога ничего не сообщает,
    # он лишь повторяет само число.
    warn_above = models.FloatField(
        "порог «выше нормы»", null=True, blank=True,
        help_text="С этого значения число начинает краснеть. Пусто — не подкрашивать.",
    )
    alarm_above = models.FloatField(
        "порог «перегрев»", null=True, blank=True,
        help_text="Значение, на котором краснота достигает предела.",
    )
    is_active = models.BooleanField("активен", default=True)
    created_at = models.DateTimeField("создан", auto_now_add=True)

    class Meta:
        verbose_name = "датчик"
        verbose_name_plural = "датчики"
        ordering = ["device", "order", "key"]
        constraints = [models.UniqueConstraint(fields=["device", "key"], name="uniq_sensor_per_device")]

    def __str__(self):
        return self.label or self.key

    @staticmethod
    def free_slot(device) -> int:
        """Наименьший незанятый слот палитры, 1..SERIES_SLOTS.

        Когда слоты кончились, начинаем круг заново: цвета повторятся, но
        восьми датчиков на площадке пока не бывает.
        """
        taken = set(device.sensors.values_list("slot", flat=True))
        for slot in range(1, SERIES_SLOTS + 1):
            if slot not in taken:
                return slot
        return (device.sensors.count() % SERIES_SLOTS) + 1

    @property
    def display_name(self) -> str:
        return self.label or self.key


class Reading(models.Model):
    """Один замер одного датчика.

    seq — сквозной счётчик пакетов на контроллере. Он нужен для идемпотентности:
    при повторной отправке (потерянное подтверждение, будущая дозаливка буфера)
    запись с той же тройкой (sensor, boot, seq) не продублируется благодаря
    уникальному ограничению ниже.

    boot — идентификатор запуска контроллера, случайный при каждом включении.
    Без него перезагрузка платы (а её вызывает даже открытие COM-порта) обнуляла
    бы seq, и новые замеры отбрасывались бы как дубликаты старых.
    """

    sensor = models.ForeignKey(
        Sensor, verbose_name="датчик", on_delete=models.CASCADE, related_name="readings"
    )
    boot = models.BigIntegerField("запуск контроллера", default=0)
    seq = models.BigIntegerField("номер пакета")
    ts = models.DateTimeField("время замера")
    value = models.FloatField("значение")
    received_at = models.DateTimeField("принято сервером", auto_now_add=True)

    class Meta:
        verbose_name = "замер"
        verbose_name_plural = "замеры"
        ordering = ["-ts"]
        constraints = [
            models.UniqueConstraint(fields=["sensor", "boot", "seq"], name="uniq_reading_per_boot_seq")
        ]
        indexes = [models.Index(fields=["sensor", "-ts"], name="idx_reading_sensor_ts")]

    def __str__(self):
        return f"{self.sensor}: {self.value} @ {self.ts:%Y-%m-%d %H:%M:%S}"
