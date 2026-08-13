from django.contrib import admin
from django.urls import include, path

from telemetry.views import live_view

admin.site.site_header = "Renovo — управление сайтом"
admin.site.site_title = "Renovo"
admin.site.index_title = "Разделы"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("telemetry.urls")),
    path("", live_view, name="home"),
    path("", include("core.urls")),
]
