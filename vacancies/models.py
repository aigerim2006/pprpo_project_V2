"""Модели каталога вакансий и справочников (ТЗ, п. 5.3 и 5.4: Vacancy, Country, ActivityField)."""
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models import EmployerProfile, LanguageLevel


class Country(models.Model):
    name = models.CharField(_("Страна"), max_length=100, unique=True)
    code = models.CharField(_("Код страны"), max_length=10, blank=True)
    is_active = models.BooleanField(_("Активна"), default=True)

    class Meta:
        verbose_name = _("Страна")
        verbose_name_plural = _("Страны")
        ordering = ["name"]

    def __str__(self):
        return self.name


class ActivityField(models.Model):
    name = models.CharField(_("Сфера деятельности"), max_length=120, unique=True)
    is_active = models.BooleanField(_("Активна"), default=True)

    class Meta:
        verbose_name = _("Сфера деятельности")
        verbose_name_plural = _("Сферы деятельности")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Vacancy(models.Model):
    employer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name="vacancies",
        verbose_name=_("Работодатель"),
    )
    title = models.CharField(_("Название вакансии"), max_length=200)
    description = models.TextField(_("Описание вакансии"))
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="vacancies",
        verbose_name=_("Страна"),
    )
    activity_field = models.ForeignKey(
        ActivityField,
        on_delete=models.PROTECT,
        related_name="vacancies",
        verbose_name=_("Сфера деятельности"),
    )
    salary_per_hour = models.DecimalField(
        _("Почасовая оплата"),
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    min_language_level = models.CharField(
        _("Минимальный уровень языка"),
        max_length=5,
        choices=LanguageLevel.choices,
        default=LanguageLevel.A2,
    )
    spots_count = models.PositiveIntegerField(
        _("Количество мест"),
        default=1,
        validators=[MinValueValidator(1)],
    )
    available_from = models.DateField(_("Начало работы"), null=True, blank=True)
    available_to = models.DateField(_("Окончание работы"), null=True, blank=True)
    is_active = models.BooleanField(_("Активна"), default=True)
    created_at = models.DateTimeField(_("Дата публикации"), auto_now_add=True)

    class Meta:
        verbose_name = _("Вакансия")
        verbose_name_plural = _("Вакансии")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.country})"

    def has_available_spots(self):
        return self.is_active and self.spots_count > 0