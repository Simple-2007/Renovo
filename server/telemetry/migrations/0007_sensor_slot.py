"""Слот палитры закрепляется за датчиком.

Раньше слот считался из позиции датчика в списке, и перестановка карточек
перекрашивала линии на графике. Существующим датчикам проставляем тот слот,
который у них был по прежней формуле, — цвета на графике не меняются.
"""
from django.db import migrations, models

SERIES_SLOTS = 8


def freeze_slots(apps, schema_editor):
    Sensor = apps.get_model("telemetry", "Sensor")
    for sensor in Sensor.objects.all():
        sensor.slot = (sensor.order % SERIES_SLOTS) + 1
        sensor.save(update_fields=["slot"])


class Migration(migrations.Migration):

    dependencies = [("telemetry", "0006_device_api_key_hash")]

    operations = [
        migrations.AddField(
            model_name="sensor",
            name="slot",
            field=models.PositiveSmallIntegerField(default=1, editable=False,
                                                   verbose_name="слот палитры"),
        ),
        migrations.RunPython(freeze_slots, migrations.RunPython.noop),
    ]
