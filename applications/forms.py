"""Формы откликов, собеседований, Job Offer и визового сопровождения."""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Application, VisaStage


class ApplicationCreateForm(forms.ModelForm):
    accept_terms = forms.BooleanField(
        label=_("Подтверждаю ознакомление с условиями вакансии и требованиями программы"),
        error_messages={"required": _("Необходимо подтвердить ознакомление с условиями.")},
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Application
        fields = ("cover_letter",)
        widgets = {
            "cover_letter": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("Кратко опишите ваш опыт и готовность к сезонной работе"),
                }
            )
        }


class EmployerDecisionForm(forms.Form):
    ACTION_REVIEWING = "REVIEWING"
    ACTION_INTERVIEW = "INTERVIEW"
    ACTION_APPROVED = "APPROVED"
    ACTION_REJECTED = "REJECTED"
    ACTION_COMPLETED = "COMPLETED"

    ACTION_CHOICES = [
        (ACTION_REVIEWING, _("На рассмотрении")),
        (ACTION_INTERVIEW, _("Назначить собеседование")),
        (ACTION_APPROVED, _("Одобрить кандидата")),
        (ACTION_REJECTED, _("Отклонить отклик")),
        (ACTION_COMPLETED, _("Завершить контракт (Опыт пройден)")),
    ]

    action = forms.ChoiceField(
        label=_("Действие по отклику"),
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    interview_date = forms.DateTimeField(
        label=_("Дата и время собеседования"),
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
    )
    interview_link_or_notes = forms.CharField(
        label=_("Ссылка / заметки к собеседованию"),
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    job_offer_terms = forms.CharField(
        label=_("Условия Job Offer"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    job_offer_file = forms.FileField(
        label=_("Файл Job Offer (PDF/JPG/PNG)"),
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}),
    )

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("action")
        if action == self.ACTION_INTERVIEW and not cleaned.get("interview_date"):
            self.add_error("interview_date", _("Укажите дату и время собеседования."))
        if action == self.ACTION_APPROVED:
            has_file = bool(cleaned.get("job_offer_file"))
            has_terms = bool((cleaned.get("job_offer_terms") or "").strip())
            if not has_file and not has_terms:
                self.add_error(
                    "job_offer_terms",
                    _("Укажите условия Job Offer или прикрепите файл предложения."),
                )
        return cleaned


class JobOfferResponseForm(forms.Form):
    DECISION_ACCEPT = "ACCEPT"
    DECISION_DECLINE = "DECLINE"

    decision = forms.ChoiceField(
        choices=[
            (DECISION_ACCEPT, _("Подтвердить Job Offer")),
            (DECISION_DECLINE, _("Отклонить Job Offer")),
        ],
        widget=forms.HiddenInput(),
    )


class VisaStageUpdateForm(forms.ModelForm):
    class Meta:
        model = VisaStage
        fields = ("stage", "authority_note", "work_permit_file")
        widgets = {
            "stage": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "authority_note": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": _("Комментарий по ZAV / Консульству"),
                }
            ),
            "work_permit_file": forms.FileInput(
                attrs={"class": "form-control form-control-sm", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
        }