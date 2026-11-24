from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.models import EmployerProfile
from .models import ActivityField, Country, Vacancy

User = get_user_model()


class VacanciesModuleTests(TestCase):
    def setUp(self):
        self.germany = Country.objects.create(name="Германия", code="DE")
        self.turkey = Country.objects.create(name="Турция", code="TR")
        self.gastro = ActivityField.objects.create(name="Гастрономия")

        self.emp_user = User.objects.create_user(
            username="emp1", email="emp1@example.com", password="Password123!", role=User.Role.EMPLOYER
        )
        self.employer = EmployerProfile.objects.create(
            user=self.emp_user,
            company_name="Karls GmbH",
            country="Германия",
            contact_person="Hans Müller",
            phone="+491512345678",
            is_verified=True,
        )
        self.vac_de = Vacancy.objects.create(
            employer=self.employer,
            title="Сервис в ресторане",
            description="Сезонная работа летом",
            country=self.germany,
            activity_field=self.gastro,
            salary_per_hour=Decimal("13.50"),
            min_language_level="A2",
            spots_count=5,
            available_from=date.today(),
            available_to=date.today() + timedelta(days=90),
            is_active=True,
        )
        Vacancy.objects.create(
            employer=self.employer,
            title="Анимация",
            description="Работа в отеле",
            country=self.turkey,
            activity_field=self.gastro,
            salary_per_hour=Decimal("8.00"),
            min_language_level="A1",
            spots_count=3,
            is_active=True,
        )

    def test_filter_by_country(self):
        resp = self.client.get(reverse("vacancies:list"), {"country": self.germany.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Сервис в ресторане")
        self.assertNotContains(resp, "Анимация")

    def test_employer_can_toggle_vacancy(self):
        self.client.force_login(self.emp_user)
        resp = self.client.post(reverse("vacancies:toggle_active", args=[self.vac_de.pk]))
        self.assertEqual(resp.status_code, 302)
        self.vac_de.refresh_from_db()
        self.assertFalse(self.vac_de.is_active)