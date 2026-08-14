from django.urls import path

from . import views

app_name = "telemetry"

urlpatterns = [
    path("readings", views.IngestView.as_view(), name="ingest"),
    path("whoami", views.WhoAmIView.as_view(), name="whoami"),
    path("latest", views.LatestView.as_view(), name="latest"),
    path("series", views.SeriesView.as_view(), name="series"),
    path("sensor-order", views.SensorOrderView.as_view(), name="sensor-order"),
]
