"""Ключ API больше не хранится в открытом виде — только его отпечаток.

Существующие ключи хешируются на месте, поэтому шлюзы продолжают работать
со своими прежними ключами: на стороне контроллера менять ничего не нужно.
Обратная миграция вернуть ключи не может — из отпечатка их не достать,
поэтому выдаёт новые.
"""
import hashlib
import secrets

from django.db import migrations, models


def sha256(value: str) -> str:
    # Считаем прямо здесь, а не зовём telemetry.models: миграция должна
    # пережить любые будущие правки кода.
    return hashlib.sha256(value.strip().encode()).hexdigest()


def hash_existing_keys(apps, schema_editor):
    Device = apps.get_model("telemetry", "Device")
    for device in Device.objects.all():
        device.api_key_hash = sha256(device.api_key)
        device.api_key_prefix = device.api_key[:8]
        device.save(update_fields=["api_key_hash", "api_key_prefix"])


def issue_new_keys(apps, schema_editor):
    Device = apps.get_model("telemetry", "Device")
    for device in Device.objects.all():
        device.api_key = secrets.token_urlsafe(32)
        device.save(update_fields=["api_key"])


class Migration(migrations.Migration):

    dependencies = [("telemetry", "0005_device_site_timezone")]

    operations = [
        migrations.AddField(
            model_name="device",
            name="api_key_hash",
            field=models.CharField(default="", editable=False, max_length=64,
                                   verbose_name="отпечаток ключа"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="device",
            name="api_key_prefix",
            field=models.CharField(
                blank=True, editable=False, max_length=12,
                help_text="Первые символы — чтобы узнать ключ, не показывая его целиком.",
                verbose_name="начало ключа",
            ),
        ),
        migrations.AddField(
            model_name="device",
            name="api_key_issued_at",
            field=models.DateTimeField(blank=True, editable=False, null=True,
                                       verbose_name="ключ выпущен"),
        ),
        migrations.RunPython(hash_existing_keys, issue_new_keys),
        migrations.AlterField(
            model_name="device",
            name="api_key_hash",
            field=models.CharField(editable=False, max_length=64, unique=True,
                                   verbose_name="отпечаток ключа"),
        ),
        migrations.RemoveField(model_name="device", name="api_key"),
    ]
