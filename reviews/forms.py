from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Review


class ReviewForm(forms.ModelForm):
    RATING_CHOICES = [
        (5, _("5 — Отлично")),
        (4, _("4 — Хорошо")),
        (3, _("3 — Удовлетворительно")),
        (2, _("2 — Ниже среднего")),
        (1, _("1 — Неудовлетворительно")),
    ]

    rating = forms.TypedChoiceField(
        label=_("Оценка работодателя (1–5)"),
        choices=RATING_CHOICES,
        coerce=int,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": _("Опишите условия работы, проживание, отношение работодателя и соответствие условиям контракта"),
                }
            )
        }