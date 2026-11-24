from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("doc_type", "student", "status", "expire_date", "upload_date")
    list_filter = ("doc_type", "status")
    search_fields = ("student__first_name", "student__last_name", "student__user__username")