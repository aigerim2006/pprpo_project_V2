from django import forms
from django.utils.translation import gettext_lazy as _

from applications.models import Application
from vacancies.models import Country


class ReportFilterForm(forms.Form):
    country = forms.ModelChoiceField(
        label=_("Страна"),
        queryset=Country.objects.all(),
        required=False,
        empty_label=_("Все страны"),
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    status = forms.ChoiceField(
        label=_("Статус заявки"),
        choices=[("", _("Все статусы"))] + list(Application.Status.choices),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )