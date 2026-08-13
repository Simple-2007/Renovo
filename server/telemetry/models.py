import secrets

from django.db import models
from django.utils import timezone

# Число слотов в категориальной палитре. Цвета живут в CSS (свои для светлой
# и тёмной темы), сюда приходит только номер слота: датчик получает его один
# раз при заведении и больше не меняет, поэтому выключение серии на графике
# никого не перекрашивает.
SERIES_SLOTS = 8


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


class Device(models.Model):
    """Контроллер-источник данных (Arduino UNO через шлюз на ПК)."""

    name = models.CharField("название", max_length=100)
    slug = models.SlugField("код", max_length=50, unique=True)
    api_key = models.CharField("ключ API", max_length=64, unique=True, default=generate_api_key)
    is_active = models.BooleanField("активно", default=True)
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

    @property
    def slot(self) -> int:
        """Номер слота палитры, 1..SERIES_SLOTS."""
        return (self.order % SERIES_SLOTS) + 1

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
