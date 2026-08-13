from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("razdel/<slug:slug>/", views.section_view, name="section"),
    path("stranica/<slug:slug>/", views.page_view, name="page"),
]
