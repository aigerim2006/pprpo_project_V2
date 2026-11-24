"""Модели модуля обработки откликов, Job Offer и визовых этапов (FR-1.5, 1.6, 2.3–2.5, 3.3)."""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from users.models import StudentProfile
from vacancies.models import Vacancy


def job_offer_upload_path(instance, filename):
    return f"job_offers/app_{instance.pk or 'new'}/{filename}"


def work_permit_upload_path(instance, filename):
    return f"work_permits/app_{instance.pk or 'new'}/{filename}"


class Application(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW", _("Новая")
        REVIEWING = "REVIEWING", _("На рассмотрении")
        INTERVIEW = "INTERVIEW", _("Собеседование")
        APPROVED = "APPROVED", _("Одобрена")
        REJECTED = "REJECTED", _("Отклонена")
        WITHDRAWN = "WITHDRAWN", _("Отозвана")
        COMPLETED = "COMPLETED", _("Завершена / Опыт пройден")

    class OfferStatus(models.TextChoices):
        NONE = "NONE", _("Не отправлен")
        SENT = "SENT", _("Ожидает подтверждения студентом")
        ACCEPTED = "ACCEPTED", _("Подтверждён студентом")
        DECLINED = "DECLINED", _("Отклонён студентом")

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name=_("Студент"),
    )
    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name=_("Вакансия"),
    )
    status = models.CharField(
        _("Статус заявки"),
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    cover_letter = models.TextField(_("Сопроводительный комментарий"), blank=True)
    interview_date = models.DateTimeField(_("Дата и время собеседования"), null=True, blank=True)
    interview_link_or_notes = models.CharField(
        _("Ссылка / заметки к собеседованию"), max_length=255, blank=True
    )
    job_offer_file = models.FileField(
        _("Файл Job Offer"), upload_to=job_offer_upload_path, null=True, blank=True
    )
    job_offer_terms = models.TextField(_("Условия Job Offer"), blank=True)
    offer_status = models.CharField(
        _("Статус Job Offer"),
        max_length=20,
        choices=OfferStatus.choices,
        default=OfferStatus.NONE,
    )
    offer_responded_at = models.DateTimeField(_("Дата ответа по Job Offer"), null=True, blank=True)
    applied_at = models.DateTimeField(_("Дата отклика"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Отклик")
        verbose_name_plural = _("Отклики")
        ordering = ["-applied_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "vacancy"], name="unique_student_vacancy_application"
            )
        ]

    def __str__(self):
        return f"{self.student} -> {self.vacancy}"

    def set_status(self, new_status):
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])

    def can_withdraw(self):
        if self.status in (self.Status.REJECTED, self.Status.WITHDRAWN, self.Status.COMPLETED):
            return False
        if self.vacancy.available_from:
            days_left = (self.vacancy.available_from - timezone.localdate()).days
            return days_left >= 180
        return True


class VisaStage(models.Model):
    class Stage(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", _("Не начато")
        APPOINTMENT = "APPOINTMENT", _("Термин / Запись")
        UNDER_REVIEW = "UNDER_REVIEW", _("На рассмотрении (ZAV / Консульство)")
        DECISION = "DECISION", _("Подтверждение / Решение")
        FOR_ISSUANCE = "FOR_ISSUANCE", _("На выдачу")
        ISSUED = "ISSUED", _("Виза / Разрешение получено")
        REFUSED = "REFUSED", _("Отказ")

    STAGE_PROGRESS = {
        Stage.NOT_STARTED: 10,
        Stage.APPOINTMENT: 30,
        Stage.UNDER_REVIEW: 55,
        Stage.DECISION: 75,
        Stage.FOR_ISSUANCE: 85,
        Stage.ISSUED: 100,
        Stage.REFUSED: 100,
    }

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="visa_stage",
        verbose_name=_("Отклик / Контракт"),
    )
    stage = models.CharField(
        _("Этап оформления"),
        max_length=25,
        choices=Stage.choices,
        default=Stage.NOT_STARTED,
    )
    authority_note = models.TextField(_("Примечание координатора (ZAV / Консульство)"), blank=True)
    work_permit_file = models.FileField(
        _("Разрешение на работу"), upload_to=work_permit_upload_path, null=True, blank=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_visa_stages",
        verbose_name=_("Координатор"),
    )
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Визовый этап")
        verbose_name_plural = _("Визовые этапы")

    def __str__(self):
        return f"{self.application.student} — {self.get_stage_display()}"

    @property
    def progress_percent(self):
        return self.STAGE_PROGRESS.get(self.stage, 0)