"""Представления модуля откликов, собеседований, Job Offer и визового сопровождения."""
import os
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from documents.models import Document
from notifications.services import notify_coordinators, notify_user
from vacancies.models import Vacancy
from .forms import (
    ApplicationCreateForm,
    EmployerDecisionForm,
    JobOfferResponseForm,
    VisaStageUpdateForm,
)
from .models import Application, VisaStage


def _student_eligibility_error(student_profile, vacancy):
    if not student_profile.is_verified:
        return _("Подача откликов доступна после верификации профиля и документов координатором.")
    verified_docs = student_profile.documents.filter(status=Document.Status.VERIFIED)
    if not verified_docs.exists():
        return _("Загрузите и пройдите верификацию базовых документов перед подачей отклика.")
    if not student_profile.is_eligible_for_vacancy(vacancy.min_language_level):
        return _("Требуется уровень языка %(req)s; ваш подтверждённый уровень — %(cur)s.") % {
            "req": vacancy.min_language_level,
            "cur": student_profile.language_level,
        }
    if vacancy.available_from and student_profile.available_from > vacancy.available_from:
        return _("Ваш период доступности начинается позже начала работы по вакансии.")
    if not vacancy.has_available_spots():
        return _("По вакансии нет свободных мест или набор закрыт.")
    return ""


@login_required
@require_POST
def apply_to_vacancy(request, vacancy_id):
    if not request.user.is_student:
        raise PermissionDenied
    student = getattr(request.user, "student_profile", None)
    if not student:
        raise PermissionDenied

    vacancy = get_object_or_404(
        Vacancy.objects.select_related("employer", "employer__user"), pk=vacancy_id, is_active=True
    )
    error_msg = _student_eligibility_error(student, vacancy)
    if error_msg:
        messages.error(request, error_msg)
        return redirect("vacancies:detail", pk=vacancy.pk)

    if Application.objects.filter(student=student, vacancy=vacancy).exists():
        messages.warning(request, _("Вы уже подавали отклик на эту вакансию."))
        return redirect("applications:list")

    form = ApplicationCreateForm(request.POST)
    if not form.is_valid():
        for err_list in form.errors.values():
            for err in err_list:
                messages.error(request, err)
        return redirect("vacancies:detail", pk=vacancy.pk)

    with transaction.atomic():
        app = Application.objects.create(
            student=student,
            vacancy=vacancy,
            status=Application.Status.REVIEWING,
            cover_letter=form.cleaned_data["cover_letter"].strip(),
        )
        VisaStage.objects.create(application=app, stage=VisaStage.Stage.NOT_STARTED)

    notify_user(
        recipient=vacancy.employer.user,
        title=_("Новый отклик на вакансию"),
        message=_("Студент %(student)s откликнулся на вакансию «%(vacancy)s».")
        % {"student": student.get_full_name(), "vacancy": vacancy.title},
        link=f"/applications/{app.pk}/",
    )
    messages.success(request, _("Отклик отправлен работодателю."))
    return redirect("applications:detail", pk=app.pk)


@login_required
def application_list(request):
    if request.user.is_student:
        student = getattr(request.user, "student_profile", None)
        qs = (
            Application.objects.filter(student=student).select_related(
                "vacancy", "vacancy__country", "vacancy__employer", "visa_stage"
            )
            if student
            else Application.objects.none()
        )
        return render(
            request,
            "applications/application_list.html",
            {"applications": qs, "role_mode": "student"},
        )

    if request.user.is_employer:
        employer = getattr(request.user, "employer_profile", None)
        qs = (
            Application.objects.filter(vacancy__employer=employer).select_related(
                "student", "student__user", "vacancy", "visa_stage"
            )
            if employer
            else Application.objects.none()
        )
        return render(
            request,
            "applications/application_list.html",
            {"applications": qs, "role_mode": "employer"},
        )

    if request.user.is_coordinator:
        return redirect("applications:coordinator_visas")

    raise PermissionDenied


@login_required
def application_detail(request, pk):
    app = get_object_or_404(
        Application.objects.select_related(
            "student",
            "student__user",
            "vacancy",
            "vacancy__country",
            "vacancy__activity_field",
            "vacancy__employer",
            "vacancy__employer__user",
        ).prefetch_related("student__documents"),
        pk=pk,
    )
    visa_stage, _created_visa = VisaStage.objects.get_or_create(application=app)

    is_owner_student = (
        request.user.is_student and getattr(request.user, "student_profile", None) == app.student
    )
    is_owner_employer = (
        request.user.is_employer
        and getattr(request.user, "employer_profile", None) == app.vacancy.employer
    )
    if not (is_owner_student or is_owner_employer or request.user.is_coordinator):
        raise PermissionDenied

    decision_form = EmployerDecisionForm() if is_owner_employer else None
    offer_form = JobOfferResponseForm() if is_owner_student else None
    student_docs = (
        app.student.documents.all()
        if (is_owner_employer or request.user.is_coordinator)
        else []
    )

    return render(
        request,
        "applications/application_detail.html",
        {
            "application": app,
            "visa_stage": visa_stage,
            "decision_form": decision_form,
            "offer_form": offer_form,
            "student_docs": student_docs,
            "is_owner_student": is_owner_student,
            "is_owner_employer": is_owner_employer,
        },
    )


@login_required
@require_POST
def employer_decide(request, pk):
    app = get_object_or_404(
        Application.objects.select_related("student", "student__user", "vacancy", "vacancy__employer"),
        pk=pk,
    )
    if (
        not request.user.is_employer
        or getattr(request.user, "employer_profile", None) != app.vacancy.employer
    ):
        raise PermissionDenied

    form = EmployerDecisionForm(request.POST, request.FILES)
    if not form.is_valid():
        for err_list in form.errors.values():
            for err in err_list:
                messages.error(request, err)
        return redirect("applications:detail", pk=app.pk)

    action = form.cleaned_data["action"]
    if action == EmployerDecisionForm.ACTION_REVIEWING:
        app.set_status(Application.Status.REVIEWING)
        notify_user(
            recipient=app.student.user,
            title=_("Отклик на рассмотрении"),
            message=_("Работодатель перевёл отклик по вакансии «%(vacancy)s» в статус «На рассмотрении».")
            % {"vacancy": app.vacancy.title},
            link=f"/applications/{app.pk}/",
        )
        messages.success(request, _("Статус отклика обновлён на «На рассмотрении»."))

    elif action == EmployerDecisionForm.ACTION_INTERVIEW:
        app.interview_date = form.cleaned_data["interview_date"]
        app.interview_link_or_notes = form.cleaned_data["interview_link_or_notes"].strip()
        app.status = Application.Status.INTERVIEW
        app.save(update_fields=["interview_date", "interview_link_or_notes", "status", "updated_at"])
        notify_user(
            recipient=app.student.user,
            title=_("Назначено собеседование"),
            message=_("По вакансии «%(vacancy)s» назначено собеседование: %(dt)s.")
            % {
                "vacancy": app.vacancy.title,
                "dt": timezone.localtime(app.interview_date).strftime("%d.%m.%Y %H:%M"),
            },
            link=f"/applications/{app.pk}/",
        )
        messages.success(request, _("Собеседование назначено, студент уведомлён."))

    elif action == EmployerDecisionForm.ACTION_APPROVED:
        if form.cleaned_data.get("job_offer_file"):
            app.job_offer_file = form.cleaned_data["job_offer_file"]
        if form.cleaned_data.get("job_offer_terms"):
            app.job_offer_terms = form.cleaned_data["job_offer_terms"].strip()
        app.offer_status = Application.OfferStatus.SENT
        app.status = Application.Status.APPROVED
        app.save()
        notify_user(
            recipient=app.student.user,
            title=_("Получен Job Offer"),
            message=_("Работодатель направил предложение о работе (Job Offer) по вакансии «%(vacancy)s».")
            % {"vacancy": app.vacancy.title},
            link=f"/applications/{app.pk}/",
        )
        messages.success(request, _("Job Offer направлен студенту."))

    elif action == EmployerDecisionForm.ACTION_REJECTED:
        app.set_status(Application.Status.REJECTED)
        notify_user(
            recipient=app.student.user,
            title=_("Отклик отклонён"),
            message=_("По вакансии «%(vacancy)s» получен отказ.") % {"vacancy": app.vacancy.title},
            link=f"/applications/{app.pk}/",
        )
        messages.info(request, _("Отклик переведён в статус «Отклонена»."))

    elif action == EmployerDecisionForm.ACTION_COMPLETED:
        app.set_status(Application.Status.COMPLETED)
        notify_user(
            recipient=app.student.user,
            title=_("Сезонная работа завершена"),
            message=_("Статус по вакансии «%(vacancy)s» обновлён на «Завершена / Опыт пройден».")
            % {"vacancy": app.vacancy.title},
            link=f"/applications/{app.pk}/",
        )
        messages.success(request, _("Статус обновлён на «Завершена / Опыт пройден»."))

    return redirect("applications:detail", pk=app.pk)


@login_required
@require_POST
def respond_job_offer(request, pk):
    app = get_object_or_404(
        Application.objects.select_related(
            "student", "vacancy", "vacancy__employer", "vacancy__employer__user"
        ),
        pk=pk,
    )
    if not request.user.is_student or getattr(request.user, "student_profile", None) != app.student:
        raise PermissionDenied

    form = JobOfferResponseForm(request.POST)
    if form.is_valid():
        decision = form.cleaned_data["decision"]
        app.offer_responded_at = timezone.now()
        if decision == JobOfferResponseForm.DECISION_ACCEPT:
            app.offer_status = Application.OfferStatus.ACCEPTED
            app.status = Application.Status.APPROVED
            app.save(update_fields=["offer_status", "status", "offer_responded_at", "updated_at"])
            VisaStage.objects.get_or_create(application=app)
            notify_user(
                recipient=app.vacancy.employer.user,
                title=_("Job Offer подтверждён студентом"),
                message=_("Студент %(student)s подтвердил Job Offer по вакансии «%(vacancy)s».")
                % {"student": app.student.get_full_name(), "vacancy": app.vacancy.title},
                link=f"/applications/{app.pk}/",
            )
            notify_coordinators(
                title=_("Новый подтверждённый Job Offer для визового сопровождения"),
                message=_("Студент %(student)s подтвердил Job Offer (%(vacancy)s).")
                % {"student": app.student.get_full_name(), "vacancy": app.vacancy.title},
                link="/applications/coordinator/visas/",
            )
            messages.success(request, _("Вы подтвердили Job Offer. Запущено визовое сопровождение."))
        else:
            app.offer_status = Application.OfferStatus.DECLINED
            app.save(update_fields=["offer_status", "offer_responded_at", "updated_at"])
            notify_user(
                recipient=app.vacancy.employer.user,
                title=_("Job Offer отклонён студентом"),
                message=_("Студент %(student)s отклонил Job Offer по вакансии «%(vacancy)s».")
                % {"student": app.student.get_full_name(), "vacancy": app.vacancy.title},
                link=f"/applications/{app.pk}/",
            )
            messages.info(request, _("Вы отклонили Job Offer."))
    return redirect("applications:detail", pk=app.pk)


@login_required
@require_POST
def withdraw_application(request, pk):
    app = get_object_or_404(Application.objects.select_related("student", "vacancy"), pk=pk)
    if not request.user.is_student or getattr(request.user, "student_profile", None) != app.student:
        raise PermissionDenied
    if not app.can_withdraw():
        messages.error(
            request,
            _("Отзыв заявки невозможен (менее чем за полгода до старта или заявка закрыта)."),
        )
        return redirect("applications:detail", pk=app.pk)

    app.set_status(Application.Status.WITHDRAWN)
    messages.info(request, _("Заявка отозвана."))
    return redirect("applications:list")


@login_required
def coordinator_visas(request):
    if not request.user.is_coordinator:
        raise PermissionDenied
    apps = Application.objects.select_related(
        "student", "student__user", "vacancy", "vacancy__country", "vacancy__employer", "visa_stage"
    ).exclude(status=Application.Status.REJECTED)

    rows = []
    for app in apps:
        visa, _created_visa = VisaStage.objects.get_or_create(application=app)
        rows.append(
            {
                "application": app,
                "visa": visa,
                "form": VisaStageUpdateForm(instance=visa),
            }
        )
    return render(request, "applications/coordinator_visas.html", {"rows": rows})


@login_required
@require_POST
def update_visa_stage(request, pk):
    if not request.user.is_coordinator:
        raise PermissionDenied
    app = get_object_or_404(
        Application.objects.select_related("student", "student__user", "vacancy"), pk=pk
    )
    visa, _created_visa = VisaStage.objects.get_or_create(application=app)
    form = VisaStageUpdateForm(request.POST, request.FILES, instance=visa)
    if form.is_valid():
        updated = form.save(commit=False)
        updated.updated_by = request.user
        updated.save()
        if updated.stage == VisaStage.Stage.ISSUED:
            app.set_status(Application.Status.COMPLETED)
        notify_user(
            recipient=app.student.user,
            title=_("Обновлён этап визового оформления"),
            message=_("Новый этап по заявке «%(vacancy)s»: %(stage)s (%(pct)s%%).")
            % {
                "vacancy": app.vacancy.title,
                "stage": updated.get_stage_display(),
                "pct": updated.progress_percent,
            },
            link=f"/applications/{app.pk}/",
        )
        messages.success(request, _("Этап визового оформления обновлён."))
    else:
        for err_list in form.errors.values():
            for err in err_list:
                messages.error(request, err)
    return redirect("applications:coordinator_visas")


@login_required
def download_job_offer(request, pk):
    app = get_object_or_404(Application, pk=pk)
    allowed = (
        request.user.is_coordinator
        or (request.user.is_student and getattr(request.user, "student_profile", None) == app.student)
        or (
            request.user.is_employer
            and getattr(request.user, "employer_profile", None) == app.vacancy.employer
        )
    )
    if not allowed or not app.job_offer_file or not os.path.isfile(app.job_offer_file.path):
        raise Http404(_("Файл не найден."))
    return FileResponse(
        open(app.job_offer_file.path, "rb"),
        as_attachment=True,
        filename=os.path.basename(app.job_offer_file.name),
    )


@login_required
def download_work_permit(request, pk):
    visa = get_object_or_404(
        VisaStage.objects.select_related("application", "application__student"), pk=pk
    )
    allowed = request.user.is_coordinator or (
        request.user.is_student
        and getattr(request.user, "student_profile", None) == visa.application.student
    )
    if not allowed or not visa.work_permit_file or not os.path.isfile(visa.work_permit_file.path):
        raise Http404(_("Файл не найден."))
    return FileResponse(
        open(visa.work_permit_file.path, "rb"),
        as_attachment=True,
        filename=os.path.basename(visa.work_permit_file.name),
    )
