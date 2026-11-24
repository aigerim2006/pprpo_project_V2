from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("employer", "student", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("employer__company_name", "student__first_name", "student__last_name", "comment")