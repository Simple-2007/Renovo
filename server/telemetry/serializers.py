import datetime as dt

from django.utils import timezone
from rest_framework import serializers

# Физически осмысленный диапазон. Значения за его пределами — это не температура,
# а признак неисправности: DS18B20 отдаёт -127 при обрыве линии и 85 при
# обращении до готовности преобразования.
VALUE_MIN = -100.0
VALUE_MAX = 300.0


class ReadingIngestSerializer(serializers.Serializer):
    """Один пакет замеров от контроллера.

    Формат:
        {"boot": 815623, "seq": 1421, "age": 0, "t": {"s1": 23.5, "s2": 24.1}}

    boot — идентификатор запуска контроллера, случайный при каждом включении.
           Отличает пакеты после перезагрузки платы от старых с тем же seq.
    seq — сквозной номер пакета на контроллере (для идемпотентности).
    ts  — абсолютное время замера. Присылается, если у контроллера есть часы
          (модуль RTC). Имеет приоритет над age.
    age — возраст замера в миллисекундах на момент отправки. Запасной вариант
          для контроллеров без часов: сервер считает ts = now - age.
          Для живых данных age = 0, при дозаливке буфера — больше нуля.
    t   — словарь {ключ_датчика: значение}. Число ключей произвольное.

    Диапазон значений здесь намеренно не проверяется: сбойный датчик не должен
    отбрасывать замеры исправных, поэтому отсев делает представление,
    отбрасывая отдельные ключи, а не весь пакет.
    """

    boot = serializers.IntegerField(min_value=0, default=0)
    seq = serializers.IntegerField(min_value=0)
    ts = serializers.DateTimeField(required=False, default=None)
    age = serializers.IntegerField(min_value=0, default=0)
    t = serializers.DictField(child=serializers.FloatField(), allow_empty=False)

    def validate_t(self, value):
        for key in value:
            if len(key) > 32:
                raise serializers.ValidationError(f"Ключ датчика '{key[:32]}…' длиннее 32 символов")
        return value

    def validate_ts(self, value):
        """Отсекаем заведомо неверные часы контроллера.

        Если RTC потерял питание, он отдаёт что-нибудь вроде 2000-01-01, и такие
        замеры лучше отклонить с внятной ошибкой, чем засорить ими историю.
        """
        if value is None:
            return None
        now = timezone.now()
        if value > now + dt.timedelta(hours=1):
            raise serializers.ValidationError(
                "Время замера в будущем — проверьте часы контроллера (RTC)")
        if value < now - dt.timedelta(days=30):
            raise serializers.ValidationError(
                "Время замера старше 30 суток — вероятно, сбились часы контроллера (RTC)")
        return value

    def validate_age(self, value):
        # Ограничиваем 30 сутками, чтобы сбойный счётчик millis() не создал
        # записи с датой в далёком прошлом.
        if value > 30 * 24 * 60 * 60 * 1000:
            raise serializers.ValidationError("Возраст замера больше 30 суток")
        return value
