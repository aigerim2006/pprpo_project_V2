"""Модель внутренних уведомлений АИС ЗСТС (FR-1.7)."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Получатель"),
    )
    title = models.CharField(_("Заголовок"), max_length=200)
    message = models.TextField(_("Сообщение"))
    link = models.CharField(_("Ссылка"), max_length=255, blank=True)
    is_read = models.BooleanField(_("Прочитано"), default=False)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)

    class Meta:
        verbose_name = _("Уведомление")
        verbose_name_plural = _("Уведомления")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"