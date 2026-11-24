"""Представления каталога вакансий и управления справочниками."""
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from users.models import LANGUAGE_LEVEL_ORDER, LanguageLevel
from .forms import ActivityFieldForm, CountryForm, VacancyForm
from .models import ActivityField, Country, Vacancy


def _get_employer_profile(user):
    if not user.is_authenticated or not user.is_employer:
        raise PermissionDenied
    profile = getattr(user, "employer_profile", None)
    if not profile:
        raise PermissionDenied
    return profile


def _require_coordinator(user):
    if not user.is_authenticated or not user.is_coordinator:
        raise PermissionDenied


def vacancy_list(request):
    queryset = Vacancy.objects.select_related("country", "activity_field", "employer").filter(is_active=True)

    country_id = request.GET.get("country", "").strip()
    activity_id = request.GET.get("activity_field", "").strip()
    min_salary = request.GET.get("min_salary", "").strip()
    max_level = request.GET.get("language_level", "").strip()
    search_q = request.GET.get("q", "").strip()

    if country_id.isdigit():
        queryset = queryset.filter(country_id=int(country_id))
    if activity_id.isdigit():
        queryset = queryset.filter(activity_field_id=int(activity_id))
    if min_salary:
        try:
            queryset = queryset.filter(salary_per_hour__gte=Decimal(min_salary))
        except InvalidOperation:
            pass
    if max_level in LANGUAGE_LEVEL_ORDER:
        allowed_levels = LANGUAGE_LEVEL_ORDER[: LANGUAGE_LEVEL_ORDER.index(max_level) + 1]
        queryset = queryset.filter(min_language_level__in=allowed_levels)
    if search_q:
        queryset = queryset.filter(title__icontains=search_q)

    student_profile = (
        getattr(request.user, "student_profile", None)
        if request.user.is_authenticated and request.user.is_student
        else None
    )

    cards = []
    for vac in queryset:
        eligible = True
        reason = ""
        if student_profile:
            if not student_profile.is_verified:
                eligible = False
                reason = _("Профиль не верифицирован")
            elif not student_profile.is_eligible_for_vacancy(vac.min_language_level):
                eligible = False
                reason = _("Требуется уровень языка %(req)s (у вас %(cur)s)") % {
                    "req": vac.min_language_level,
                    "cur": student_profile.language_level,
                }
        cards.append({"vacancy": vac, "eligible": eligible, "reason": reason})

    return render(
        request,
        "vacancies/vacancy_list.html",
        {
            "cards": cards,
            "countries": Country.objects.filter(is_active=True),
            "activity_fields": ActivityField.objects.filter(is_active=True),
            "language_levels": LanguageLevel.choices,
            "filters": {
                "country": country_id,
                "activity_field": activity_id,
                "min_salary": min_salary,
                "language_level": max_level,
                "q": search_q,
            },
        },
    )


def vacancy_detail(request, pk):
    vacancy = get_object_or_404(
        Vacancy.objects.select_related("country", "activity_field", "employer"),
        pk=pk,
    )
    if not vacancy.is_active and not (
        request.user.is_authenticated
        and (
            request.user.is_coordinator
            or (request.user.is_employer and getattr(request.user, "employer_profile", None) == vacancy.employer)
        )
    ):
        raise PermissionDenied

    student_profile = (
        getattr(request.user, "student_profile", None)
        if request.user.is_authenticated and request.user.is_student
        else None
    )
    can_apply = False
    block_reason = ""
    if student_profile:
        if not student_profile.is_verified:
            block_reason = _("Подача откликов доступна после верификации профиля и документов координатором.")
        elif not student_profile.is_eligible_for_vacancy(vacancy.min_language_level):
            block_reason = _("Требуется уровень языка %(req)s; ваш уровень — %(cur)s.") % {
                "req": vacancy.min_language_level,
                "cur": student_profile.language_level,
            }
        elif not vacancy.has_available_spots():
            block_reason = _("Набор по вакансии закрыт или нет свободных мест.")
        else:
            can_apply = True

    return render(
        request,
        "vacancies/vacancy_detail.html",
        {
            "vacancy": vacancy,
            "can_apply": can_apply,
            "block_reason": block_reason,
        },
    )


@login_required
def vacancy_create(request):
    employer = _get_employer_profile(request.user)
    if not employer.is_verified:
        messages.warning(request, _("Публикация вакансий доступна после верификации компании координатором."))
        return redirect("users:dashboard")

    if request.method == "POST":
        form = VacancyForm(request.POST)
        if form.is_valid():
            vacancy = form.save(commit=False)
            vacancy.employer = employer
            vacancy.save()
            messages.success(request, _("Вакансия опубликована."))
            return redirect("vacancies:detail", pk=vacancy.pk)
    else:
        form = VacancyForm()
    return render(request, "vacancies/vacancy_form.html", {"form": form, "is_edit": False})


@login_required
def vacancy_edit(request, pk):
    employer = _get_employer_profile(request.user)
    vacancy = get_object_or_404(Vacancy, pk=pk, employer=employer)
    if request.method == "POST":
        form = VacancyForm(request.POST, instance=vacancy)
        if form.is_valid():
            form.save()
            messages.success(request, _("Вакансия обновлена."))
            return redirect("vacancies:detail", pk=vacancy.pk)
    else:
        form = VacancyForm(instance=vacancy)
    return render(
        request,
        "vacancies/vacancy_form.html",
        {"form": form, "vacancy": vacancy, "is_edit": True},
    )


@login_required
@require_POST
def vacancy_toggle_active(request, pk):
    employer = _get_employer_profile(request.user)
    vacancy = get_object_or_404(Vacancy, pk=pk, employer=employer)
    vacancy.is_active = not vacancy.is_active
    vacancy.save(update_fields=["is_active"])
    messages.info(
        request,
        _("Вакансия открыта для откликов.") if vacancy.is_active else _("Вакансия закрыта."),
    )
    return redirect("vacancies:detail", pk=vacancy.pk)


@login_required
def coordinator_catalogs(request):
    _require_coordinator(request.user)
    country_form = CountryForm(prefix="country")
    activity_form = ActivityFieldForm(prefix="activity")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_country":
            country_form = CountryForm(request.POST, prefix="country")
            if country_form.is_valid():
                country_form.save()
                messages.success(request, _("Страна добавлена в справочник."))
                return redirect("vacancies:catalogs")
        elif action == "add_activity":
            activity_form = ActivityFieldForm(request.POST, prefix="activity")
            if activity_form.is_valid():
                activity_form.save()
                messages.success(request, _("Сфера деятельности добавлена в справочник."))
                return redirect("vacancies:catalogs")

    return render(
        request,
        "vacancies/coordinator_catalogs.html",
        {
            "countries": Country.objects.all(),
            "activity_fields": ActivityField.objects.all(),
            "country_form": country_form,
            "activity_form": activity_form,
        },
    )