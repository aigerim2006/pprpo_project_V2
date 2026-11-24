"""Модели модуля документооборота (ТЗ, п. 5.3 и 5.4: Document)."""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from users.models import StudentProfile
from .validators import validate_document_file


def student_document_upload_path(instance, filename):
    return f"documents/student_{instance.student_id}/{filename}"


class Document(models.Model):
    class DocType(models.TextChoices):
        PASSPORT = "PASSPORT", _("Загранпаспорт")
        STUDY_CERT = "STUDY_CERT", _("Справка с места учебы")
        CV = "CV", _("Резюме / CV")
        LANG_CERT = "LANG_CERT", _("Языковой сертификат")

    class Status(models.TextChoices):
        PENDING = "PENDING", _("На проверке")
        VERIFIED = "VERIFIED", _("Верифицирован")
        REJECTED = "REJECTED", _("Отклонен")

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("Студент"),
    )
    doc_type = models.CharField(
        _("Тип документа"), max_length=30, choices=DocType.choices
    )
    file = models.FileField(
        _("Файл документа"),
        upload_to=student_document_upload_path,
        validators=[validate_document_file],
    )
    issue_date = models.DateField(_("Дата выдачи"), null=True, blank=True)
    expire_date = models.DateField(_("Срок действия"), null=True, blank=True)
    status = models.CharField(
        _("Статус проверки"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    rejection_reason = models.TextField(_("Причина отклонения"), blank=True)
    upload_date = models.DateTimeField(_("Дата загрузки"), auto_now_add=True)
    reviewed_at = models.DateTimeField(_("Дата проверки"), null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_documents",
        verbose_name=_("Проверил координатор"),
    )

    class Meta:
        verbose_name = _("Документ")
        verbose_name_plural = _("Документы")
        ordering = ["-upload_date"]

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.student}"

    def is_expired(self):
        if not self.expire_date:
            return False
        return self.expire_date < timezone.localdate()