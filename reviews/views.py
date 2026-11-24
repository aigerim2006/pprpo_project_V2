"""Представления отзывов о работодателях с проверкой статуса COMPLETED (FR-1.8, UC-14)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from applications.models import Application
from users.models import EmployerProfile
from .forms import ReviewForm
from .models import Review


def review_list(request):
    employer_id = request.GET.get("employer", "").strip()
    reviews = Review.objects.select_related(
        "student", "employer", "application", "application__vacancy"
    )
    selected_employer = None
    if employer_id.isdigit():
        selected_employer = EmployerProfile.objects.filter(pk=int(employer_id)).first()
        if selected_employer:
            reviews = reviews.filter(employer=selected_employer)

    completed_apps = []
    if request.user.is_authenticated and request.user.is_student:
        student = getattr(request.user, "student_profile", None)
        if student:
            completed_apps = Application.objects.filter(
                student=student,
                status=Application.Status.COMPLETED,
                review__isnull=True,
            ).select_related("vacancy", "vacancy__employer")

    employers = list(
        EmployerProfile.objects.filter(is_verified=True)
        .annotate(avg_rating=Avg("reviews__rating"))
        .order_by("-avg_rating", "company_name")
    )
    for emp in employers:
        emp.computed_rating = (
            round(float(emp.avg_rating), 2) if emp.avg_rating is not None else 0.0
        )

    return render(
        request,
        "reviews/review_list.html",
        {
            "reviews": reviews,
            "employers": employers,
            "selected_employer": selected_employer,
            "completed_apps": completed_apps,
        },
    )


@login_required
def create_review(request, application_id):
    if not request.user.is_student:
        raise PermissionDenied
    student = getattr(request.user, "student_profile", None)
    app = get_object_or_404(
        Application.objects.select_related("vacancy", "vacancy__employer"),
        pk=application_id,
        student=student,
    )

    if app.status != Application.Status.COMPLETED:
        messages.warning(
            request,
            _("Функция доступна только после фактического завершения срока действия трудового договора."),
        )
        return redirect("applications:detail", pk=app.pk)

    if hasattr(app, "review"):
        messages.info(request, _("Вы уже оставили отзыв по этому контракту."))
        return redirect("reviews:list")

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.application = app
            review.student = student
            review.employer = app.vacancy.employer
            review.save()
            messages.success(request, _("Спасибо! Ваш отзыв опубликован, рейтинг работодателя обновлён."))
            return redirect("reviews:list")
    else:
        form = ReviewForm()

    return render(
        request,
        "reviews/review_form.html",
        {"form": form, "application": app},
    )
