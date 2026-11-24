"""Представления модуля документооборота и верификации студентов."""
import os
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from notifications.services import notify_coordinators, notify_user
from users.models import StudentProfile
from .forms import DocumentReviewForm, DocumentUploadForm
from .models import Document


def _require_student_profile(user):
    if not user.is_authenticated or not user.is_student:
        raise PermissionDenied
    profile = getattr(user, "student_profile", None)
    if not profile:
        raise PermissionDenied
    return profile


def _require_coordinator(user):
    if not user.is_authenticated or not user.is_coordinator:
        raise PermissionDenied


@login_required
def document_list(request):
    profile = _require_student_profile(request.user)
    docs = Document.objects.filter(student=profile)
    return render(
        request,
        "documents/document_list.html",
        {"profile": profile, "documents": docs},
    )


@login_required
def document_upload(request):
    profile = _require_student_profile(request.user)
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.student = profile
            doc.status = Document.Status.PENDING
            doc.rejection_reason = ""
            doc.save()

            if profile.is_verified:
                profile.is_verified = False
                profile.save(update_fields=["is_verified"])

            notify_coordinators(
                title=_("Новый документ на проверку"),
                message=_("Студент %(student)s загрузил документ: %(doc_type)s.")
                % {"student": profile.get_full_name(), "doc_type": doc.get_doc_type_display()},
                link="/documents/coordinator/",
            )
            messages.success(request, _("Документ отправлен на проверку координатору."))
            return redirect("documents:list")
    else:
        form = DocumentUploadForm()
    return render(request, "documents/document_form.html", {"form": form, "is_edit": False})


@login_required
def document_edit(request, pk):
    profile = _require_student_profile(request.user)
    doc = get_object_or_404(Document, pk=pk, student=profile)
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES, instance=doc)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.status = Document.Status.PENDING
            updated.rejection_reason = ""
            updated.reviewed_at = None
            updated.reviewed_by = None
            updated.save()

            notify_coordinators(
                title=_("Документ обновлён"),
                message=_("Студент %(student)s обновил документ: %(doc_type)s.")
                % {"student": profile.get_full_name(), "doc_type": doc.get_doc_type_display()},
                link="/documents/coordinator/",
            )
            messages.success(request, _("Документ обновлён и направлен на повторную проверку."))
            return redirect("documents:list")
    else:
        form = DocumentUploadForm(instance=doc)
    return render(
        request,
        "documents/document_form.html",
        {"form": form, "document": doc, "is_edit": True},
    )


@login_required
@require_POST
def document_delete(request, pk):
    profile = _require_student_profile(request.user)
    doc = get_object_or_404(Document, pk=pk, student=profile)
    if doc.file and os.path.isfile(doc.file.path):
        doc.file.delete(save=False)
    doc.delete()
    messages.info(request, _("Документ удалён."))
    return redirect("documents:list")


@login_required
def document_download(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if request.user.is_coordinator:
        pass
    elif request.user.is_student and getattr(request.user, "student_profile", None) == doc.student:
        pass
    else:
        raise PermissionDenied

    if not doc.file or not os.path.isfile(doc.file.path):
        raise Http404(_("Файл не найден."))

    return FileResponse(open(doc.file.path, "rb"), as_attachment=True, filename=os.path.basename(doc.file.name))


@login_required
def coordinator_documents(request):
    _require_coordinator(request.user)
    status_filter = request.GET.get("status", "")
    docs = Document.objects.select_related("student", "student__user")
    if status_filter in dict(Document.Status.choices):
        docs = docs.filter(status=status_filter)

    students = StudentProfile.objects.select_related("user").prefetch_related("documents")
    return render(
        request,
        "documents/coordinator_documents.html",
        {
            "documents": docs,
            "students": students,
            "status_filter": status_filter,
            "status_choices": Document.Status.choices,
        },
    )


@login_required
@require_POST
def review_document(request, pk):
    _require_coordinator(request.user)
    doc = get_object_or_404(Document.objects.select_related("student", "student__user"), pk=pk)
    form = DocumentReviewForm(request.POST)
    if form.is_valid():
        decision = form.cleaned_data["decision"]
        reason = form.cleaned_data["rejection_reason"].strip()
        doc.reviewed_at = timezone.now()
        doc.reviewed_by = request.user
        if decision == DocumentReviewForm.DECISION_VERIFY:
            doc.status = Document.Status.VERIFIED
            doc.rejection_reason = ""
            doc.save()
            notify_user(
                recipient=doc.student.user,
                title=_("Документ верифицирован"),
                message=_("Документ «%(doc_type)s» проверен и подтверждён координатором.")
                % {"doc_type": doc.get_doc_type_display()},
                link="/documents/",
            )
            messages.success(request, _("Документ верифицирован."))
        else:
            doc.status = Document.Status.REJECTED
            doc.rejection_reason = reason
            doc.save()
            notify_user(
                recipient=doc.student.user,
                title=_("Документ отклонён"),
                message=_("Документ «%(doc_type)s» отклонён. Причина: %(reason)s")
                % {"doc_type": doc.get_doc_type_display(), "reason": reason},
                link="/documents/",
            )
            messages.warning(request, _("Документ отклонён, студенту отправлено уведомление."))
    else:
        for err_list in form.errors.values():
            for err in err_list:
                messages.error(request, err)
    return redirect("documents:coordinator_list")


@login_required
@require_POST
def toggle_student_verification(request, student_id):
    _require_coordinator(request.user)
    student = get_object_or_404(StudentProfile.objects.select_related("user"), pk=student_id)
    student.is_verified = not student.is_verified
    student.save(update_fields=["is_verified"])

    if student.is_verified:
        notify_user(
            recipient=student.user,
            title=_("Профиль студента верифицирован"),
            message=_("Ваш профиль верифицирован координатором. Теперь доступен отклик на вакансии."),
            link="/vacancies/",
        )
        messages.success(request, _("Профиль студента верифицирован."))
    else:
        notify_user(
            recipient=student.user,
            title=_("Верификация профиля снята"),
            message=_("Статус верификации вашего профиля изменён на «Ожидает верификации»."),
            link="/documents/",
        )
        messages.info(request, _("Статус верификации студента обновлён."))

    return redirect("documents:coordinator_list")