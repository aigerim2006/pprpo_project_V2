"""Модель отзывов о работодателях и расчёт среднего рейтинга (FR-1.8, UC-14)."""
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.utils.translation import gettext_lazy as _

from applications.models import Application
from users.models import EmployerProfile, StudentProfile


class Review(models.Model):
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="review",
        verbose_name=_("Завершённый контракт"),
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("Студент"),
    )
    employer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("Работодатель"),
    )
    rating = models.PositiveSmallIntegerField(
        _("Оценка (1–5)"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(_("Отзыв об условиях труда и программе"))
    created_at = models.DateTimeField(_("Дата публикации"), auto_now_add=True)

    class Meta:
        verbose_name = _("Отзыв о работодателе")
        verbose_name_plural = _("Отзывы о работодателях")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employer.company_name} ({self.rating}/5) — {self.student}"

    @staticmethod
    def get_employer_rating(employer) -> Decimal:
        avg_val = employer.reviews.aggregate(avg=Avg("rating"))["avg"]
        if avg_val is None:
            return Decimal("0.00")
        return Decimal(str(round(float(avg_val), 2)))
