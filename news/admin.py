from django.contrib import admin
from .models import News


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "audience", "relevant_until", "is_published", "created_at")
    list_filter = ("audience", "is_published")
    search_fields = ("title", "content")