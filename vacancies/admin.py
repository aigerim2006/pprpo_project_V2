from django.contrib import admin
from .models import ActivityField, Country, Vacancy


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)


@admin.register(ActivityField)
class ActivityFieldAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "country", "activity_field", "salary_per_hour", "min_language_level", "is_active")
    list_filter = ("country", "activity_field", "min_language_level", "is_active")
    search_fields = ("title", "employer__company_name")