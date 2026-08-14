from django.contrib import admin
from django.utils.html import format_html

from .models import Device, Reading, Sensor


# Перетаскивание строк расставляет номера в поле «порядок», а сохраняет
# пользователь обычной кнопкой формы: своего эндпоинта для порядка нет,
# и незасохранённая перестановка просто пропадает при уходе со страницы.
class DragOrderMedia:
    class Media:
        css = {"all": ("telemetry/admin-order.css",)}
        js = ("telemetry/admin-order.js",)


class SensorInline(admin.TabularInline):
    model = Sensor
    extra = 0
    fields = ("key", "label", "unit", "color", "order", "warn_above", "alarm_above", "is_active")


@admin.register(Device)
class DeviceAdmin(DragOrderMedia, admin.ModelAdmin):
    list_display = ("name", "slug", "status", "sensor_count", "site_timezone",
                    "last_seen_at", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("api_key", "last_seen_at", "created_at")
    inlines = [SensorInline]

    @admin.display(description="состояние")
    def status(self, obj):
        color, text = ("#2e7d32", "на связи") if obj.is_online else ("#b71c1c", "нет связи")
        return format_html('<b style="color:{}">{}</b>', color, text)

    @admin.display(description="датчиков")
    def sensor_count(self, obj):
        return obj.sensors.count()


@admin.register(Sensor)
class SensorAdmin(DragOrderMedia, admin.ModelAdmin):
    list_display = ("display_name", "device", "key", "unit", "swatch", "order",
                    "warn_above", "alarm_above", "is_active")
    list_filter = ("device", "is_active")
    search_fields = ("key", "label")
    list_editable = ("order", "warn_above", "alarm_above", "is_active")

    @admin.display(description="цвет")
    def swatch(self, obj):
        if obj.color:
            return format_html(
                '<span style="display:inline-block;width:22px;height:12px;background:{};'
                'border:1px solid #999"></span> {}', obj.color, obj.color,
            )
        return f"слот {obj.slot}"


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ("ts", "sensor", "value", "seq", "received_at")
    list_filter = ("sensor__device", "sensor")
    date_hierarchy = "ts"
    ordering = ("-ts",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
