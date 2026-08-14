from django.contrib import admin
from django.http import Http404
from django.template.response import TemplateResponse
from django.urls import path, reverse
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
    readonly_fields = ("api_key_state", "last_seen_at", "created_at")
    inlines = [SensorInline]

    def get_urls(self):
        return [
            path(
                "<path:object_id>/rotate-key/",
                self.admin_site.admin_view(self.rotate_key_view),
                name="telemetry_device_rotate_key",
            ),
            *super().get_urls(),
        ]

    @admin.display(description="ключ API")
    def api_key_state(self, obj):
        """Ключа в базе нет — показываем начало и ссылку на перевыпуск."""
        if obj is None or not obj.pk:
            return "Ключ будет показан один раз после сохранения."
        issued = obj.api_key_issued_at
        when = f", выпущен {issued:%d.%m.%Y}" if issued else ""
        return format_html(
            '<span style="font-family:monospace">{}…</span>'
            '<span style="color:#666"> — целиком показан только при выпуске{}</span><br>'
            '<a class="button" style="margin-top:6px;display:inline-block" href="{}">'
            "Перевыпустить ключ</a>",
            obj.api_key_prefix or "—", when,
            reverse("admin:telemetry_device_rotate_key", args=[obj.pk]),
        )

    def save_model(self, request, obj, form, change):
        # Новое устройство сразу получает ключ: без него шлюзу не с чем идти.
        # Показать его надо один раз, поэтому передаём в ответ отдельной
        # страницей — см. response_add.
        if not obj.api_key_hash:
            self._issued_key = obj.issue_api_key()
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        key = getattr(self, "_issued_key", None)
        self._issued_key = None
        if key:
            return self._key_page(request, obj, key)
        return super().response_add(request, obj, post_url_continue)

    def _key_page(self, request, device, key):
        """Страница с только что выпущенным ключом.

        Отдельной страницей, а не сообщением в шапке: ключ показывается
        единственный раз, и его нужно успеть скопировать — в общей ленте
        уведомлений он теряется среди прочего и пропадает при переходе.
        """
        return TemplateResponse(request, "admin/telemetry/device/key_issued.html", {
            **self.admin_site.each_context(request),
            "title": "Ключ API выпущен",
            "device": device,
            "api_key": key,
            "opts": self.opts,
        })

    def rotate_key_view(self, request, object_id):
        """Перевыпуск ключа. Старый перестаёт работать сразу же."""
        device = self.get_object(request, object_id)
        if device is None:
            raise Http404("Устройство не найдено")
        if not self.has_change_permission(request, device):
            raise Http404("Нет прав на изменение устройства")

        if request.method == "POST":
            key = device.issue_api_key()
            device.save(update_fields=["api_key_hash", "api_key_prefix", "api_key_issued_at"])
            self.log_change(request, device, "Перевыпущен ключ API")
            return self._key_page(request, device, key)

        return TemplateResponse(request, "admin/telemetry/device/rotate_key.html", {
            **self.admin_site.each_context(request),
            "title": "Перевыпуск ключа API",
            "device": device,
            "opts": self.opts,
        })

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
