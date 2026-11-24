from django.urls import path
from . import views

app_name = "vacancies"

urlpatterns = [
    path("", views.vacancy_list, name="list"),
    path("<int:pk>/", views.vacancy_detail, name="detail"),
    path("create/", views.vacancy_create, name="create"),
    path("<int:pk>/edit/", views.vacancy_edit, name="edit"),
    path("<int:pk>/toggle/", views.vacancy_toggle_active, name="toggle_active"),
    path("coordinator/catalogs/", views.coordinator_catalogs, name="catalogs"),
]