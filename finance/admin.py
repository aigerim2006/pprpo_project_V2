from django.contrib import admin
from .models import Invoice, Payment


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "student", "service_type", "amount_total", "amount_paid", "status", "created_at")
    list_filter = ("status", "service_type")
    search_fields = ("number", "student__first_name", "student__last_name", "description")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "invoice", "amount", "status", "card_last4", "created_at")
    list_filter = ("status",)
    search_fields = ("transaction_id", "invoice__number")