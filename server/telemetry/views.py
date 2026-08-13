import datetime as dt

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Device, Reading, Sensor
from .serializers import VALUE_MAX, VALUE_MIN, ReadingIngestSerializer

MAX_BATCH = 500


def _device_from_key(request) -> Device | None:
    """Аутентификация устройства по заголовку X-Device-Key."""
    key = request.headers.get("X-Device-Key", "").strip()
    if not key:
        return None
    return Device.objects.filter(api_key=key, is_active=True).first()


def _resolve_device(slug: str | None) -> Device:
    """Устройство по slug, либо первое активное — чтобы тестовая страница
    работала без настройки сразу после подключения контроллера."""
    if slug:
        return get_object_or_404(Device, slug=slug, is_active=True)
    device = Device.objects.filter(is_active=True).first()
    if device is None:
        raise Http404("Активных устройств нет")
    return device


class IngestView(APIView):
    """POST /api/v1/readings — приём замеров от контроллера.

    Принимает как один пакет, так и массив пакетов (пригодится для дозаливки
    накопленного буфера — серверная часть к этому уже готова).
    """

    def post(self, request):
        device = _device_from_key(request)
        if device is None:
            return Response({"ok": False, "error": "Неизвестный или неактивный ключ устройства"},
                            status=status.HTTP_401_UNAUTHORIZED)

        payload = request.data if isinstance(request.data, list) else [request.data]
        if len(payload) > MAX_BATCH:
            return Response({"ok": False, "error": f"За один запрос не более {MAX_BATCH} пакетов"},
                            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        serializer = ReadingIngestSerializer(data=payload, many=True)
        if not serializer.is_valid():
            return Response({"ok": False, "error": "Некорректный формат", "detail": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        packets = serializer.validated_data
        now = timezone.now()

        # Отсев неисправных датчиков: выбрасываем только сбойные значения,
        # исправные замеры из того же пакета сохраняем.
        skipped: set[str] = set()
        for packet in packets:
            good = {k: v for k, v in packet["t"].items() if VALUE_MIN <= v <= VALUE_MAX}
            skipped.update(packet["t"].keys() - good.keys())
            packet["t"] = good
        packets = [p for p in packets if p["t"]]

        if not packets:
            return Response({
                "ok": False,
                "error": "Все значения вне допустимого диапазона",
                "skipped": sorted(skipped),
            }, status=status.HTTP_400_BAD_REQUEST)

        # Датчики заводятся на лету: любой новый ключ в пакете сразу становится
        # датчиком с автоцветом. Ограничения на их количество нет.
        sensors: dict[str, Sensor] = {}
        for key in sorted({k for packet in packets for k in packet["t"]}):
            sensor = Sensor.objects.filter(device=device, key=key).first()
            if sensor is None:
                next_order = Sensor.objects.filter(device=device).count()
                sensor, _ = Sensor.objects.get_or_create(
                    device=device, key=key, defaults={"order": next_order},
                )
            sensors[key] = sensor

        rows = [
            Reading(
                sensor=sensors[key],
                boot=packet["boot"],
                seq=packet["seq"],
                ts=packet["ts"] or now - dt.timedelta(milliseconds=packet["age"]),
                value=value,
            )
            for packet in packets
            for key, value in packet["t"].items()
        ]

        # ignore_conflicts делает повтор отправки безопасным: тройка
        # (sensor, boot, seq) уникальна, дубликаты отбрасываются на уровне БД.
        with transaction.atomic():
            Reading.objects.bulk_create(rows, ignore_conflicts=True)
            device.last_seen_at = now
            device.save(update_fields=["last_seen_at"])

        # ack отдаём только после коммита: контроллер удалит из буфера ровно то,
        # что действительно легло в базу.
        return Response({
            "ok": True,
            "ack": max(p["seq"] for p in packets),
            "received": len(rows),
            "skipped": sorted(skipped),
            "now": int(now.timestamp()),
        })


class WhoAmIView(APIView):
    """GET /api/v1/whoami — проверка ключа устройства без записи данных.

    Нужна при удалённой настройке: позволяет убедиться, что ключ верный и
    сервер доступен, не засоряя историю пробными замерами.
    """

    def get(self, request):
        device = _device_from_key(request)
        if device is None:
            return Response({"ok": False, "error": "Неизвестный или неактивный ключ устройства"},
                            status=status.HTTP_401_UNAUTHORIZED)
        return Response({
            "ok": True,
            "device": {
                "name": device.name,
                "slug": device.slug,
                "interval": device.report_interval_sec,
                "online": device.is_online,
                "last_seen": device.last_seen_at.isoformat() if device.last_seen_at else None,
            },
            "sensors": [s.key for s in device.sensors.filter(is_active=True)],
            "readings_total": Reading.objects.filter(sensor__device=device).count(),
            "server_time": timezone.now().isoformat(),
        })


class LatestView(APIView):
    """GET /api/v1/latest — последнее значение по каждому датчику."""

    def get(self, request):
        device = _resolve_device(request.query_params.get("device"))
        latest = (
            Reading.objects
            .filter(sensor__device=device, sensor__is_active=True)
            .order_by("sensor_id", "-ts")
            .distinct("sensor_id")
            .select_related("sensor")
        )
        by_sensor = {r.sensor_id: r for r in latest}

        sensors = []
        for sensor in device.sensors.filter(is_active=True):
            reading = by_sensor.get(sensor.id)
            sensors.append({
                "key": sensor.key,
                "label": sensor.display_name,
                "unit": sensor.unit,
                "slot": sensor.slot,
                "color": sensor.color,
                "warn_above": sensor.warn_above,
                "alarm_above": sensor.alarm_above,
                "value": reading.value if reading else None,
                "ts": reading.ts.isoformat() if reading else None,
                "age": round((timezone.now() - reading.ts).total_seconds(), 1) if reading else None,
            })

        return Response({
            "device": {
                "slug": device.slug,
                "name": device.name,
                "online": device.is_online,
                "interval": device.report_interval_sec,
                "stale_after": device.offline_after_sec,
            },
            "server_time": timezone.now().isoformat(),
            "sensors": sensors,
        })


class SeriesView(APIView):
    """GET /api/v1/series?minutes=30 — история по всем датчикам для графика."""

    def get(self, request):
        device = _resolve_device(request.query_params.get("device"))
        try:
            minutes = min(max(int(request.query_params.get("minutes", 30)), 1), 60 * 24 * 7)
        except ValueError:
            minutes = 30
        since = timezone.now() - dt.timedelta(minutes=minutes)

        series = []
        for sensor in device.sensors.filter(is_active=True):
            points = (
                sensor.readings.filter(ts__gte=since)
                .order_by("ts")
                .values_list("ts", "value")
            )
            series.append({
                "key": sensor.key,
                "label": sensor.display_name,
                "unit": sensor.unit,
                "slot": sensor.slot,
                "color": sensor.color,
                "points": [{"ts": ts.isoformat(), "v": v} for ts, v in points],
            })

        return Response({
            "device": {"slug": device.slug, "name": device.name, "online": device.is_online},
            "minutes": minutes,
            "series": series,
        })


def live_view(request):
    """Тестовая страница с живой трансляцией температур."""
    device = Device.objects.filter(is_active=True).first()
    return render(request, "telemetry/live.html", {"device": device})
