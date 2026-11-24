"""Формы выставления счетов координатором и оплаты через шлюз (UC-15, FR-3.6)."""
from decimal import Decimal
import re

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Invoice


class InvoiceCreateForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ("student", "application", "service_type", "description", "amount_total", "due_date")
        widgets = {
            "student": forms.Select(attrs={"class": "form-select"}),
            "application": forms.Select(attrs={"class": "form-select"}),
            "service_type": forms.Select(attrs={"class": "form-select"}),
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Например: Оформление контракта Ferienjob 2026"),
                }
            ),
            "amount_total": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0.01"}
            ),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


class PaymentGatewayForm(forms.Form):
    amount = forms.DecimalField(
        label=_("Сумма к оплате (EUR)"),
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    card_holder = forms.CharField(
        label=_("Имя держателя карты"),
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "AIGERIM KHALBEKOVA"}
        ),
    )
    card_number = forms.CharField(
        label=_("Номер банковской карты"),
        max_length=19,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "4169 5800 1234 5678"}
        ),
    )
    expiry = forms.CharField(
        label=_("Срок действия (MM/YY)"),
        max_length=5,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "08/28"}),
    )
    cvv = forms.CharField(
        label=_("CVV / CVC"),
        max_length=4,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "***"}),
    )

    def __init__(self, *args, max_amount=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_amount = max_amount
        if max_amount is not None:
            self.fields["amount"].initial = max_amount
            self.fields["amount"].widget.attrs["max"] = str(max_amount)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if self.max_amount is not None and amount > self.max_amount:
            raise forms.ValidationError(
                _("Сумма платежа не может превышать остаток задолженности (%(max)s EUR).")
                % {"max": self.max_amount}
            )
        return amount

    def clean_card_number(self):
        digits = re.sub(r"\s+", "", self.cleaned_data["card_number"])
        if not digits.isdigit() or not (13 <= len(digits) <= 19):
            raise forms.ValidationError(_("Введите корректный номер банковской карты (13–19 цифр)."))
        return digits

    def clean_expiry(self):
        val = self.cleaned_data["expiry"].strip()
        if not re.match(r"^(0[1-9]|1[0-2])/\d{2}$", val):
            raise forms.ValidationError(_("Укажите срок действия в формате MM/YY."))
        return val

    def clean_cvv(self):
        cvv = self.cleaned_data["cvv"].strip()
        if not cvv.isdigit() or len(cvv) not in (3, 4):
            raise forms.ValidationError(_("Неверный CVV/CVC код."))
        return cvv