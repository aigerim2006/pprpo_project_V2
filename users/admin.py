from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import AdminUserChangeForm, AdminUserCreationForm
from .models import EmployerProfile, StudentProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("username", "email")
    fieldsets = UserAdmin.fieldsets + ((_("Роль в системе"), {"fields": ("role",)}),)
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "last_name",
        "first_name",
        "university",
        "course",
        "language_level",
        "is_verified",
    )
    list_filter = ("is_verified", "language_level", "course")
    search_fields = ("last_name", "first_name", "university", "user__username")


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "country", "contact_person", "phone", "is_verified")
    list_filter = ("is_verified", "country")
    search_fields = ("company_name", "contact_person", "user__username")
    actions = ["verify_selected"]

    @admin.action(description=_("Верифицировать выбранные компании"))
    def verify_selected(self, request, queryset):
        for profile in queryset:
            profile.verify_company()
