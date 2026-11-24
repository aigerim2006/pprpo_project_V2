"""Валидаторы приложения users."""
from datetime import date

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MIN_AGE = 18  # ТЗ, п. 2.3: соискатели — лица, достигшие 18 лет


def calculate_age(born, today=None):
    today = today or date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def validate_adult(value):
    if calculate_age(value) < MIN_AGE:
        raise ValidationError(
            _("Регистрация доступна только лицам, достигшим 18 лет.")
        )
