"""Представления приложения users."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import (
    EmployerProfileForm,
    EmployerRegistrationForm,
    LoginForm,
    StudentProfileForm,
    StudentRegistrationForm,
)
from .models import EmployerProfile, StudentProfile, User
from .permissions import role_required

DASHBOARD_TEMPLATES = {
    User.Role.STUDENT: "users/dashboard_student.html",
    User.Role.EMPLOYER: "users/dashboard_employer.html",
    User.Role.COORDINATOR: "users/dashboard_coordinator.html",
}


class UserLoginView(LoginView):
    template_name = "users/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def _register(request, form_class, template, success_message):
    if request.user.is_authenticated:
        return redirect("users:dashboard")
    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, success_message)
        return redirect("users:dashboard")
    return render(request, template, {"form": form})


def register_student(request):
    return _register(
        request,
        StudentRegistrationForm,
        "users/register_student.html",
        _("Регистрация прошла успешно. Добро пожаловать в личный кабинет!"),
    )


def register_employer(request):
    return _register(
        request,
        EmployerRegistrationForm,
        "users/register_employer.html",
        _(
            "Компания зарегистрирована. Доступ к публикации вакансий откроется "
            "после верификации координатором."
        ),
    )


@login_required
def dashboard(request):
    """Личный кабинет: содержимое зависит от роли."""
    user = request.user
    context = {"profile": user.get_profile()}
    if user.is_coordinator:
        context["stats"] = {
            "users": User.objects.count(),
            "students": StudentProfile.objects.count(),
            "employers": EmployerProfile.objects.count(),
            "employers_pending": EmployerProfile.objects.filter(
                is_verified=False, user__is_active=True
            ).count(),
        }
    return render(request, DASHBOARD_TEMPLATES[user.role], context)


@login_required
def profile(request):
    """Ведение личного профиля (FR-1.2) — студент и работодатель."""
    user = request.user
    if user.is_coordinator:
        return redirect("users:dashboard")
    form_class = StudentProfileForm if user.is_student else EmployerProfileForm
    form = form_class(request.POST or None, instance=user.get_profile())
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = user
        obj.save()
        messages.success(request, _("Профиль сохранён."))
        return redirect("users:profile")
    return render(request, "users/profile.html", {"form": form})


# --- Панель координатора (FR-2.1/3.1 — верификация компаний, FR-3.5) ---------
def _safe_next(request, default="users:coordinator_users"):
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(target)
    return redirect(default)


@role_required(User.Role.COORDINATOR)
def coordinator_users(request):
    users = User.objects.select_related("student_profile", "employer_profile").order_by(
        "-date_joined"
    )
    role = request.GET.get("role", "")
    query = request.GET.get("q", "").strip()
    pending = request.GET.get("verification") == "pending"

    if role in User.Role.values:
        users = users.filter(role=role)
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(student_profile__last_name__icontains=query)
            | Q(employer_profile__company_name__icontains=query)
        )
    if pending:
        users = users.filter(
            Q(employer_profile__is_verified=False) | Q(student_profile__is_verified=False)
        )

    params = request.GET.copy()
    params.pop("page", None)
    page = Paginator(users, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "users/coordinator_users.html",
        {
            "page": page,
            "roles": User.Role.choices,
            "current_role": role,
            "query": query,
            "pending": pending,
            "querystring": params.urlencode(),
        },
    )


@role_required(User.Role.COORDINATOR)
@require_POST
def user_toggle_active(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        messages.error(request, _("Нельзя деактивировать собственную учётную запись."))
    else:
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        text = (
            _("Учётная запись «%(name)s» активирована.")
            if target.is_active
            else _("Учётная запись «%(name)s» деактивирована.")
        )
        messages.success(request, text % {"name": target.username})
    return _safe_next(request)


@role_required(User.Role.COORDINATOR)
@require_POST
def employer_verify(request, pk):
    profile_obj = get_object_or_404(EmployerProfile, user_id=pk)
    profile_obj.verify_company()
    messages.success(
        request,
        _("Компания «%(name)s» верифицирована.") % {"name": profile_obj.company_name},
    )
    return _safe_next(request)
