"""Формы приложения users: регистрация, вход, профили."""
import re
from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import EmployerProfile, LanguageLevel, StudentProfile, User, phone_validator
from .validators import MIN_AGE, validate_adult

DATE_FORMAT = "%Y-%m-%d"
PHONE_PATTERN = r"\+?[0-9 \-\(\)]{10,18}"

PERSON_NAME_RE = re.compile(r"^[А-Яа-яЁёA-Za-z][А-Яа-яЁёA-Za-z\s'\-]{1,98}[А-Яа-яЁёA-Za-z]$")
COUNTRY_RE = re.compile(r"^[А-Яа-яЁёA-Za-z][А-Яа-яЁёA-Za-z\s\-]{1,98}[А-Яа-яЁёA-Za-z]$")
COMPANY_RE = re.compile(r"^[А-Яа-яЁёA-Za-z0-9][А-Яа-яЁёA-Za-z0-9\s\-&.,\"'«»№]{1,250}$")
ACADEMIC_TEXT_RE = re.compile(r"^[А-Яа-яЁёA-Za-z0-9][А-Яа-яЁёA-Za-z0-9\s\-.,()\"'«»]{2,250}$")
HAS_LETTER_RE = re.compile(r"[А-Яа-яЁёA-Za-z]")
ONLY_DIGITS_RE = re.compile(r"^\d+$")
REPEATED_CHARS_RE = re.compile(r"(.)\1{3,}", re.IGNORECASE)


def date_widget(**attrs):
    return forms.DateInput(attrs={"type": "date", **attrs}, format=DATE_FORMAT)


def validate_person_name(value, field_label=_("Поле")):
    val = " ".join((value or "").strip().split())
    if len(val) < 2:
        raise ValidationError(_("%(field)s должно содержать минимум 2 символа.") % {"field": field_label})
    if ONLY_DIGITS_RE.match(val) or not HAS_LETTER_RE.search(val):
        raise ValidationError(_("%(field)s должно содержать буквы, а не только цифры или символы.") % {"field": field_label})
    if not PERSON_NAME_RE.match(val):
        raise ValidationError(
            _("%(field)s может содержать только буквы, пробел, дефис и апостроф.") % {"field": field_label}
        )
    if REPEATED_CHARS_RE.search(val):
        raise ValidationError(_("%(field)s содержит недопустимый повтор символов.") % {"field": field_label})
    return val


def validate_country_name(value):
    val = " ".join((value or "").strip().split())
    if len(val) < 2 or not COUNTRY_RE.match(val) or REPEATED_CHARS_RE.search(val):
        raise ValidationError(_("Введите корректное название страны (только буквы, от 2 символов)."))
    return val


def validate_company_name(value):
    val = " ".join((value or "").strip().split())
    if len(val) < 2 or ONLY_DIGITS_RE.match(val) or not HAS_LETTER_RE.search(val):
        raise ValidationError(_("Введите корректное название компании (минимум 2 символа, не только цифры)."))
    if not COMPANY_RE.match(val) or REPEATED_CHARS_RE.search(val):
        raise ValidationError(_("Название компании содержит некорректные символы."))
    return val


def validate_academic_field(value, field_label=_("Поле")):
    val = " ".join((value or "").strip().split())
    if len(val) < 3 or ONLY_DIGITS_RE.match(val) or not HAS_LETTER_RE.search(val):
        raise ValidationError(
            _("%(field)s должно содержать минимум 3 символа и включать буквы (не только цифры).")
            % {"field": field_label}
        )
    if not ACADEMIC_TEXT_RE.match(val) or REPEATED_CHARS_RE.search(val):
        raise ValidationError(_("%(field)s содержит некорректные символы или повтор символов.") % {"field": field_label})
    return val


def validate_strict_phone(value):
    phone_validator(value)
    digits = re.sub(r"\D", "", value or "")
    if len(digits) < 9 or len(digits) > 15:
        raise ValidationError(_("Номер телефона должен содержать от 9 до 15 цифр."))
    if len(set(digits)) == 1:
        raise ValidationError(_("Введите реальный номер телефона, а не повторяющиеся цифры."))
    return (value or "").strip()


class BootstrapFormMixin:
    """Добавляет классы Bootstrap 5 и подсветку полей с ошибками."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                widget = self.fields[name].widget
                widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()


def check_availability_period(form, cleaned):
    start, end = cleaned.get("available_from"), cleaned.get("available_to")
    today = timezone.localdate()
    if start and start < today:
        form.add_error(
            "available_from",
            _("Дата начала доступности не может быть раньше сегодняшнего дня."),
        )
    if start and end and end < start:
        form.add_error(
            "available_to", _("Дата окончания не может быть раньше даты начала.")
        )


# --- Вход ------------------------------------------------------------------
class LoginForm(BootstrapFormMixin, AuthenticationForm):
    error_messages = {
        "invalid_login": _("Неверный логин или пароль"),
        "inactive": _("Учётная запись деактивирована."),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("Логин")
        self.fields["password"].label = _("Пароль")


# --- Регистрация студента (FR-1.1, FR-1.2) ----------------------------------
class StudentRegistrationForm(BootstrapFormMixin, UserCreationForm):
    first_name = forms.CharField(
        label=_("Имя"),
        min_length=2,
        max_length=100,
        widget=forms.TextInput(attrs={"data-validate": "name"}),
    )
    last_name = forms.CharField(
        label=_("Фамилия"),
        min_length=2,
        max_length=100,
        widget=forms.TextInput(attrs={"data-validate": "name"}),
    )
    birth_date = forms.DateField(
        label=_("Дата рождения"),
        widget=date_widget(**{"data-min-age": MIN_AGE}),
        validators=[validate_adult],
        help_text=_("Регистрация доступна лицам, достигшим 18 лет."),
    )
    university = forms.CharField(
        label=_("ВУЗ"),
        min_length=3,
        max_length=255,
        widget=forms.TextInput(attrs={"data-validate": "academic"}),
    )
    field_of_study = forms.CharField(
        label=_("Направление подготовки"),
        min_length=3,
        max_length=255,
        widget=forms.TextInput(attrs={"data-validate": "academic"}),
    )
    course = forms.IntegerField(
        label=_("Курс"),
        min_value=1,
        max_value=6,
        widget=forms.NumberInput(attrs={"min": 1, "max": 6, "data-validate": "course"}),
    )
    language_level = forms.ChoiceField(
        label=_("Уровень владения иностранным языком"),
        choices=[("", "---------")] + LanguageLevel.choices,
    )
    available_from = forms.DateField(
        label=_("Доступен для работы с"), widget=date_widget()
    )
    available_to = forms.DateField(
        label=_("Доступен для работы по"),
        widget=date_widget(**{"data-after": "id_available_from"}),
    )
    is_full_time = forms.BooleanField(
        label=_("Подтверждаю, что являюсь студентом очной формы обучения"),
        error_messages={
            "required": _("Регистрация доступна только студентам очной формы обучения.")
        },
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("Логин")
        self.fields["username"].widget.attrs["data-validate"] = "username"
        self.fields["email"].label = _("Email")
        self.fields["email"].required = True
        self.fields["email"].widget.attrs["data-validate"] = "email"
        self.fields["password1"].label = _("Пароль")
        self.fields["password2"].label = _("Подтверждение пароля")
        self.fields["password2"].widget.attrs["data-match"] = "id_password1"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Пользователь с таким email уже существует."))
        return email

    def clean_first_name(self):
        return validate_person_name(self.cleaned_data.get("first_name"), _("Имя"))

    def clean_last_name(self):
        return validate_person_name(self.cleaned_data.get("last_name"), _("Фамилия"))

    def clean_university(self):
        return validate_academic_field(self.cleaned_data.get("university"), _("Название ВУЗа"))

    def clean_field_of_study(self):
        return validate_academic_field(
            self.cleaned_data.get("field_of_study"), _("Направление подготовки")
        )

    def clean(self):
        cleaned = super().clean()
        check_availability_period(self, cleaned)
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.save()
        data = self.cleaned_data
        StudentProfile.objects.create(
            user=user,
            first_name=data["first_name"],
            last_name=data["last_name"],
            birth_date=data["birth_date"],
            university=data["university"],
            field_of_study=data["field_of_study"],
            course=data["course"],
            language_level=data["language_level"],
            available_from=data["available_from"],
            available_to=data["available_to"],
        )
        return user


# --- Регистрация работодателя (FR-2.1) -------------------------------------
class EmployerRegistrationForm(BootstrapFormMixin, UserCreationForm):
    company_name = forms.CharField(
        label=_("Название компании"),
        min_length=2,
        max_length=255,
        widget=forms.TextInput(attrs={"data-validate": "company"}),
    )
    country = forms.CharField(
        label=_("Страна"),
        min_length=2,
        max_length=100,
        widget=forms.TextInput(attrs={"data-validate": "country"}),
    )
    contact_person = forms.CharField(
        label=_("Контактное лицо"),
        min_length=2,
        max_length=150,
        widget=forms.TextInput(attrs={"data-validate": "name"}),
    )
    phone = forms.CharField(
        label=_("Телефон"),
        max_length=30,
        validators=[validate_strict_phone],
        widget=forms.TextInput(
            attrs={"type": "tel", "pattern": PHONE_PATTERN, "data-validate": "phone"}
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("Логин")
        self.fields["username"].widget.attrs["data-validate"] = "username"
        self.fields["email"].label = _("Email")
        self.fields["email"].required = True
        self.fields["email"].widget.attrs["data-validate"] = "email"
        self.fields["password1"].label = _("Пароль")
        self.fields["password2"].label = _("Подтверждение пароля")
        self.fields["password2"].widget.attrs["data-match"] = "id_password1"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Пользователь с таким email уже существует."))
        return email

    def clean_company_name(self):
        return validate_company_name(self.cleaned_data.get("company_name"))

    def clean_country(self):
        return validate_country_name(self.cleaned_data.get("country"))

    def clean_contact_person(self):
        return validate_person_name(self.cleaned_data.get("contact_person"), _("Контактное лицо"))

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.EMPLOYER
        user.save()
        data = self.cleaned_data
        EmployerProfile.objects.create(
            user=user,
            company_name=data["company_name"],
            country=data["country"],
            contact_person=data["contact_person"],
            phone=data["phone"],
        )
        return user


# --- Редактирование профилей (FR-1.2) ---------------------------------------
class StudentProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = (
            "first_name",
            "last_name",
            "birth_date",
            "university",
            "field_of_study",
            "course",
            "language_level",
            "available_from",
            "available_to",
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"data-validate": "name"}),
            "last_name": forms.TextInput(attrs={"data-validate": "name"}),
            "birth_date": date_widget(**{"data-min-age": MIN_AGE}),
            "university": forms.TextInput(attrs={"data-validate": "academic"}),
            "field_of_study": forms.TextInput(attrs={"data-validate": "academic"}),
            "course": forms.NumberInput(attrs={"min": 1, "max": 6, "data-validate": "course"}),
            "available_from": date_widget(),
            "available_to": date_widget(**{"data-after": "id_available_from"}),
        }

    def clean_first_name(self):
        return validate_person_name(self.cleaned_data.get("first_name"), _("Имя"))

    def clean_last_name(self):
        return validate_person_name(self.cleaned_data.get("last_name"), _("Фамилия"))

    def clean_university(self):
        return validate_academic_field(self.cleaned_data.get("university"), _("Название ВУЗа"))

    def clean_field_of_study(self):
        return validate_academic_field(
            self.cleaned_data.get("field_of_study"), _("Направление подготовки")
        )

    def clean(self):
        cleaned = super().clean()
        check_availability_period(self, cleaned)
        return cleaned


class EmployerProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ("company_name", "country", "contact_person", "phone")
        widgets = {
            "company_name": forms.TextInput(attrs={"data-validate": "company"}),
            "country": forms.TextInput(attrs={"data-validate": "country"}),
            "contact_person": forms.TextInput(attrs={"data-validate": "name"}),
            "phone": forms.TextInput(
                attrs={"type": "tel", "pattern": PHONE_PATTERN, "data-validate": "phone"}
            ),
        }

    def clean_company_name(self):
        return validate_company_name(self.cleaned_data.get("company_name"))

    def clean_country(self):
        return validate_country_name(self.cleaned_data.get("country"))

    def clean_contact_person(self):
        return validate_person_name(self.cleaned_data.get("contact_person"), _("Контактное лицо"))

    def clean_phone(self):
        return validate_strict_phone(self.cleaned_data.get("phone"))


# --- Формы для панели администрирования (кастомная модель User) --------------
class AdminUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "role")


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User