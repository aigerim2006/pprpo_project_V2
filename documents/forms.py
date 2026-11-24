"""Формы загрузки, редактирования и проверки документов."""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Document


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ("doc_type", "file", "issue_date", "expire_date")
        widgets = {
            "doc_type": forms.Select(attrs={"class": "form-select"}),
            "file": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),
            "issue_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "expire_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        issue = cleaned.get("issue_date")
        expire = cleaned.get("expire_date")
        if issue and expire and expire < issue:
            self.add_error("expire_date", _("Срок действия не может быть раньше даты выдачи."))
        return cleaned


class DocumentReviewForm(forms.Form):
    DECISION_VERIFY = "VERIFY"
    DECISION_REJECT = "REJECT"
    DECISION_CHOICES = [
        (DECISION_VERIFY, _("Верифицировать")),
        (DECISION_REJECT, _("Отклонить")),
    ]

    decision = forms.ChoiceField(
        label=_("Решение"),
        choices=DECISION_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    rejection_reason = forms.CharField(
        label=_("Причина отклонения"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": _("Укажите причину при отклонении"),
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == self.DECISION_REJECT and not (cleaned.get("rejection_reason") or "").strip():
            self.add_error("rejection_reason", _("Укажите причину отклонения документа."))
        return cleaned