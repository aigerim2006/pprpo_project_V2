"""Модели приложения users (ТЗ, п. 5.3 «Диаграмма классов» и п. 5.4)."""
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .validators import calculate_age, validate_adult


class LanguageLevel(models.TextChoices):
    A1 = "A1", "A1"
    A2 = "A2", "A2"
    B1 = "B1", "B1"
    B2 = "B2", "B2"
    C1 = "C1", "C1"


LANGUAGE_LEVEL_ORDER = [level.value for level in LanguageLevel]

phone_validator = RegexValidator(
    r"^\+?[0-9 \-()]{7,20}$", _("Введите корректный номер телефона.")
)


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Суперпользователь, созданный через createsuperuser, — Координатор.
        extra_fields.setdefault("role", User.Role.COORDINATOR)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Учётная запись (таблица users_user): STUDENT / EMPLOYER / COORDINATOR."""

    class Role(models.TextChoices):
        STUDENT = "STUDENT", _("Студент")
        EMPLOYER = "EMPLOYER", _("Работодатель")
        COORDINATOR = "COORDINATOR", _("Координатор")

    email = models.EmailField(_("Email"), max_length=254, unique=True)
    role = models.CharField(
        _("Роль"), max_length=20, choices=Role.choices, default=Role.STUDENT
    )

    objects = CustomUserManager()

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        # Доступ к панели администрирования имеют только Координаторы (RBAC).
        if self.role == self.Role.COORDINATOR:
            self.is_staff = True
        elif not self.is_superuser:
            self.is_staff = False
        super().save(*args, **kwargs)

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_employer(self):
        return self.role == self.Role.EMPLOYER

    @property
    def is_coordinator(self):
        return self.role == self.Role.COORDINATOR

    def get_profile(self):
        if self.is_student:
            return getattr(self, "student_profile", None)
        if self.is_employer:
            return getattr(self, "employer_profile", None)
        return None

    def get_full_name(self):
        profile = self.get_profile()
        name = profile.get_full_name() if profile else ""
        return name or self.username


class StudentProfile(models.Model):
    """Профиль студента (таблица users_studentprofile)."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )
    first_name = models.CharField(_("Имя"), max_length=100)
    last_name = models.CharField(_("Фамилия"), max_length=100)
    birth_date = models.DateField(_("Дата рождения"), validators=[validate_adult])
    university = models.CharField(_("ВУЗ"), max_length=255)
    field_of_study = models.CharField(_("Направление подготовки"), max_length=255)
    course = models.IntegerField(
        _("Курс"), validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    language_level = models.CharField(
        _("Уровень владения иностранным языком"),
        max_length=5,
        choices=LanguageLevel.choices,
    )
    available_from = models.DateField(_("Доступен для работы с"))
    available_to = models.DateField(_("Доступен для работы по"))
    is_verified = models.BooleanField(_("Верифицирован"), default=False)

    class Meta:
        verbose_name = _("Профиль студента")
        verbose_name_plural = _("Профили студентов")
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def age(self):
        return calculate_age(self.birth_date)

    def is_eligible_for_vacancy(self, min_level):
        """Уровень языка студента не ниже требуемого вакансией."""
        try:
            return LANGUAGE_LEVEL_ORDER.index(
                self.language_level
            ) >= LANGUAGE_LEVEL_ORDER.index(min_level)
        except ValueError:
            return False


class EmployerProfile(models.Model):
    """Профиль работодателя (компании-партнёра)."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="employer_profile"
    )
    company_name = models.CharField(_("Название компании"), max_length=255)
    country = models.CharField(_("Страна"), max_length=100)
    contact_person = models.CharField(_("Контактное лицо"), max_length=150)
    phone = models.CharField(_("Телефон"), max_length=30, validators=[phone_validator])
    is_verified = models.BooleanField(_("Верифицирована"), default=False)

    class Meta:
        verbose_name = _("Профиль работодателя")
        verbose_name_plural = _("Профили работодателей")
        ordering = ["company_name"]

    def __str__(self):
        return self.company_name

    def get_full_name(self):
        return self.contact_person

    def verify_company(self):
        self.is_verified = True
        self.save(update_fields=["is_verified"])
