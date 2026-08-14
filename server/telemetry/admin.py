from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Device, Reading, Sensor


# Ручка перетаскивания. Отдаём её отдельной колонкой, а не подсаживаем
# скриптом в чужую ячейку: в инлайне первая ячейка занята подписью строки,
# которую Django позиционирует абсолютно, и ручка с подписью налезали друг
# на друга.
GRIP_HTML = (
    '<button type="button" class="row-grip" aria-label="Переставить строку"'
    ' title="Перетащите за ручку или переставьте стрелками">'
    '<svg viewBox="0 0 16 16" aria-hidden="true">'
    '<circle cx="6" cy="4" r="1.4"/><circle cx="10" cy="4" r="1.4"/>'
    '<circle cx="6" cy="8" r="1.4"/><circle cx="10" cy="8" r="1.4"/>'
    '<circle cx="6" cy="12" r="1.4"/><circle cx="10" cy="12" r="1.4"/>'
    "</svg></button>"
)


# Перетаскивание строк расставляет номера в поле «порядок», а сохраняет
# пользователь обычной кнопкой формы: своего эндпоинта для порядка нет,
# и незасохранённая перестановка просто пропадает при уходе со страницы.
class DragOrderMixin:
    @admin.display(description="")
    def reorder_handle(self, obj=None):
        return mark_safe(GRIP_HTML)

    class Media:
        css = {"all": ("telemetry/admin-order.css",)}
        js = ("telemetry/admin-order.js",)


class SensorInline(DragOrderMixin, admin.TabularInline):
    model = Sensor
    extra = 0
    fields = ("reorder_handle", "key", "label", "unit", "color", "order",
              "warn_above", "alarm_above", "is_active")
    readonly_fields = ("reorder_handle",)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
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
class SensorAdmin(DragOrderMixin, admin.ModelAdmin):
    list_display = ("reorder_handle", "name", "device", "key", "unit", "swatch",
                    "order", "warn_above", "alarm_above", "is_active")
    # Ручка идёт первой колонкой, но ссылкой на датчик остаётся название:
    # иначе Django сделал бы ссылкой первую колонку, то есть саму ручку.
    list_display_links = ("name",)
    list_filter = ("device", "is_active")
    search_fields = ("key", "label")
    list_editable = ("order", "warn_above", "alarm_above", "is_active")

    # Заголовок колонки берётся из имени property, и в списке значилось
    # «DISPLAY NAME» — подписываем по-русски.
    @admin.display(description="название", ordering="label")
    def name(self, obj):
        return obj.display_name

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
