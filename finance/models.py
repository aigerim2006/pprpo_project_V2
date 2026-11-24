"""Модели финансового контура: счета (Invoice) и платежи (Payment) (FR-1.9, FR-3.6, UC-15)."""
from decimal import Decimal
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from applications.models import Application
from users.models import StudentProfile


def receipt_upload_path(instance, filename):
    return f"receipts/student_{instance.invoice.student_id}/{filename}"


class Invoice(models.Model):
    class ServiceType(models.TextChoices):
        CONTRACT = "CONTRACT", _("Оплата контракта по программе")
        VISA_FEE = "VISA_FEE", _("Визовый и консульский сбор")
        EXTRA = "EXTRA", _("Дополнительные услуги")

    class Status(models.TextChoices):
        UNPAID = "UNPAID", _("Не оплачен")
        PARTIAL = "PARTIAL", _("Частично оплачен")
        PAID = "PAID", _("Оплачен")
        CANCELLED = "CANCELLED", _("Отменён")

    number = models.CharField(_("Номер счёта"), max_length=32, unique=True, editable=False)
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="invoices",
        verbose_name=_("Студент"),
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
        verbose_name=_("Заявка / Контракт"),
    )
    service_type = models.CharField(
        _("Назначение платежа"),
        max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.CONTRACT,
    )
    description = models.CharField(_("Описание услуги"), max_length=255)
    amount_total = models.DecimalField(
        _("Сумма к оплате (EUR)"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    amount_paid = models.DecimalField(
        _("Оплачено (EUR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    status = models.CharField(
        _("Статус счёта"),
        max_length=20,
        choices=Status.choices,
        default=Status.UNPAID,
    )
    due_date = models.DateField(_("Срок оплаты"), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_invoices",
        verbose_name=_("Выставил координатор"),
    )
    created_at = models.DateTimeField(_("Дата выставления"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Счёт на оплату")
        verbose_name_plural = _("Счета на оплату")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.number} — {self.student} ({self.amount_total} EUR)"

    @property
    def balance_due(self):
        remaining = self.amount_total - self.amount_paid
        return remaining if remaining > Decimal("0.00") else Decimal("0.00")

    def recalculate_balance(self):
        paid = (
            self.payments.filter(status=Payment.Status.SUCCEEDED).aggregate(total=Sum("amount"))[
                "total"
            ]
            or Decimal("0.00")
        )
        self.amount_paid = paid
        if self.status != self.Status.CANCELLED:
            if paid >= self.amount_total:
                self.status = self.Status.PAID
            elif paid > Decimal("0.00"):
                self.status = self.Status.PARTIAL
            else:
                self.status = self.Status.UNPAID
        self.save(update_fields=["amount_paid", "status", "updated_at"])


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Ожидает подтверждения шлюза")
        SUCCEEDED = "SUCCEEDED", _("Оплачено")
        FAILED = "FAILED", _("Отклонено банком")

    transaction_id = models.CharField(
        _("ID транзакции шлюза"), max_length=40, unique=True, editable=False
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("Счёт"),
    )
    amount = models.DecimalField(
        _("Сумма платежа (EUR)"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    card_last4 = models.CharField(_("Последние 4 цифры карты"), max_length=4, blank=True)
    status = models.CharField(
        _("Статус платежа"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    failure_reason = models.CharField(_("Причина отказа"), max_length=255, blank=True)
    receipt_pdf = models.FileField(
        _("Электронная квитанция (PDF)"),
        upload_to=receipt_upload_path,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(_("Дата платежа"), auto_now_add=True)

    class Meta:
        verbose_name = _("Платёж")
        verbose_name_plural = _("Платежи")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_id} ({self.amount} EUR — {self.get_status_display()})"