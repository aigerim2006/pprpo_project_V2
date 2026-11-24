"""Формы вакансий и справочников (FR-2.2, FR-3.2)."""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ActivityField, Country, Vacancy


class VacancyForm(forms.ModelForm):
    class Meta:
        model = Vacancy
        fields = (
            "title",
            "country",
            "activity_field",
            "salary_per_hour",
            "min_language_level",
            "spots_count",
            "available_from",
            "available_to",
            "description",
            "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.Select(attrs={"class": "form-select"}),
            "activity_field": forms.Select(attrs={"class": "form-select"}),
            "salary_per_hour": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "min_language_level": forms.Select(attrs={"class": "form-select"}),
            "spots_count": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "available_from": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "available_to": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["country"].queryset = Country.objects.filter(is_active=True)
        self.fields["activity_field"].queryset = ActivityField.objects.filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("available_from")
        end = cleaned.get("available_to")
        if start and end and end < start:
            self.add_error("available_to", _("Дата окончания не может быть раньше даты начала."))
        return cleaned


class CountryForm(forms.ModelForm):
    class Meta:
        model = Country
        fields = ("name", "code", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ActivityFieldForm(forms.ModelForm):
    class Meta:
        model = ActivityField
        fields = ("name", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }