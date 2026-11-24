from django import forms
from django.utils.translation import gettext_lazy as _

from .models import News


class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ("title", "content", "audience", "relevant_until", "is_published")
        error_messages = {
            "title": {"required": _("Пожалуйста, заполните заголовок и текст новости.")},
            "content": {"required": _("Пожалуйста, заполните заголовок и текст новости.")},
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "audience": forms.Select(attrs={"class": "form-select"}),
            "relevant_until": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }