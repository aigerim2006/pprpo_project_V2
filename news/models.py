"""Модель новостной ленты с целевой аудиторией (FR-3.7, UC-18)."""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class News(models.Model):
    class Audience(models.TextChoices):
        ALL = "ALL", _("Для всех пользователей")
        STUDENT = "STUDENT", _("Только для студентов")
        EMPLOYER = "EMPLOYER", _("Только для работодателей")

    title = models.CharField(_("Заголовок новости"), max_length=200)
    content = models.TextField(_("Текст новости"))
    audience = models.CharField(
        _("Целевая аудитория"),
        max_length=20,
        choices=Audience.choices,
        default=Audience.ALL,
    )
    relevant_until = models.DateField(_("Актуально до"), null=True, blank=True)
    is_published = models.BooleanField(_("Опубликовано"), default=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_items",
        verbose_name=_("Автор (координатор)"),
    )
    created_at = models.DateTimeField(_("Дата публикации"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Новость")
        verbose_name_plural = _("Новости")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @classmethod
    def for_user(cls, user):
        today = timezone.localdate()
        qs = cls.objects.filter(is_published=True).filter(
            models.Q(relevant_until__isnull=True) | models.Q(relevant_until__gte=today)
        )
        if not user.is_authenticated:
            return qs.filter(audience=cls.Audience.ALL)
        if user.is_coordinator:
            return cls.objects.all()
        if user.is_student:
            return qs.filter(audience__in=[cls.Audience.ALL, cls.Audience.STUDENT])
        if user.is_employer:
            return qs.filter(audience__in=[cls.Audience.ALL, cls.Audience.EMPLOYER])
        return qs.filter(audience=cls.Audience.ALL)