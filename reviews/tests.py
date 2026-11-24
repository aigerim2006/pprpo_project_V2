from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from applications.models import Application
from users.models import EmployerProfile, LanguageLevel, StudentProfile
from vacancies.models import ActivityField, Country, Vacancy
from .models import Review

User = get_user_model()


class ReviewsModuleTests(TestCase):
    def setUp(self):
        country = Country.objects.create(name="Германия", code="DE")
        field = ActivityField.objects.create(name="Отели")
        emp_user = User.objects.create_user(
            username="emp_rev", email="emp_rev@example.com", password="Password123!", role=User.Role.EMPLOYER
        )
        self.employer = EmployerProfile.objects.create(
            user=emp_user,
            company_name="Hotel Berlin",
            country="Германия",
            contact_person="Anna",
            phone="+491512223344",
            is_verified=True,
        )
        vacancy = Vacancy.objects.create(
            employer=self.employer,
            title="Администратор",
            description="Отель",
            country=country,
            activity_field=field,
            salary_per_hour=Decimal("15.00"),
            min_language_level=LanguageLevel.B1,
            spots_count=2,
            available_from=date.today() + timedelta(days=30),
            available_to=date.today() + timedelta(days=90),
            is_active=True,
        )
        self.st_user = User.objects.create_user(
            username="st_rev", email="st_rev@example.com", password="Password123!", role=User.Role.STUDENT
        )
        self.student = StudentProfile.objects.create(
            user=self.st_user,
            first_name="Айгерим",
            last_name="Халбекова",
            birth_date=date(2006, 2, 25),
            university="КГТУ",
            field_of_study="ПИ",
            course=3,
            language_level=LanguageLevel.B1,
            available_from=date.today() + timedelta(days=20),
            available_to=date.today() + timedelta(days=100),
            is_verified=True,
        )
        self.app = Application.objects.create(
            student=self.student,
            vacancy=vacancy,
            status=Application.Status.APPROVED,
        )

    def test_review_blocked_until_completed(self):
        self.client.force_login(self.st_user)
        resp = self.client.get(reverse("reviews:create", args=[self.app.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Review.objects.count(), 0)

    def test_review_allowed_after_completed_and_recalculates_rating(self):
        self.app.set_status(Application.Status.COMPLETED)
        self.client.force_login(self.st_user)
        resp = self.client.post(
            reverse("reviews:create", args=[self.app.pk]),
            {"rating": 5, "comment": "Отличные условия и своевременная оплата."},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Review.get_employer_rating(self.employer), Decimal("5.00"))
