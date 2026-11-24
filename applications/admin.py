from django.contrib import admin
from .models import Application, VisaStage


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("student", "vacancy", "status", "offer_status", "interview_date", "applied_at")
    list_filter = ("status", "offer_status")
    search_fields = ("student__first_name", "student__last_name", "vacancy__title")


@admin.register(VisaStage)
class VisaStageAdmin(admin.ModelAdmin):
    list_display = ("application", "stage", "updated_by", "updated_at")
    list_filter = ("stage",)