from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from applications.models import Application
from users.models import EmployerProfile, LanguageLevel, StudentProfile
from vacancies.models import ActivityField, Country, Vacancy

User = get_user_model()


class ReportsModuleTests(TestCase):
    def setUp(self):
        self.coord = User.objects.create_user(
            username="coord_rep", email="coord_rep@example.com", password="Password123!", role=User.Role.COORDINATOR
        )
        self.student_user = User.objects.create_user(
            username="st_rep", email="st_rep@example.com", password="Password123!", role=User.Role.STUDENT
        )
        country = Country.objects.create(name="Германия", code="DE")
        field = ActivityField.objects.create(name="Гастрономия")
        emp_user = User.objects.create_user(
            username="emp_rep", email="emp_rep@example.com", password="Password123!", role=User.Role.EMPLOYER
        )
        employer = EmployerProfile.objects.create(
            user=emp_user,
            company_name="Karls",
            country="Германия",
            contact_person="Max",
            phone="+491519998877",
            is_verified=True,
        )
        vacancy = Vacancy.objects.create(
            employer=employer,
            title="Бариста",
            description="Кафе",
            country=country,
            activity_field=field,
            salary_per_hour=Decimal("14.50"),
            min_language_level=LanguageLevel.A2,
            spots_count=3,
            available_from=date.today() + timedelta(days=30),
            available_to=date.today() + timedelta(days=90),
            is_active=True,
        )
        student = StudentProfile.objects.create(
            user=self.student_user,
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
        Application.objects.create(student=student, vacancy=vacancy, status=Application.Status.APPROVED)

    def test_coordinator_can_export_excel_and_pdf(self):
        self.client.force_login(self.coord)
        resp_page = self.client.get(reverse("reports:dashboard"))
        self.assertEqual(resp_page.status_code, 200)

        resp_xlsx = self.client.get(reverse("reports:export_excel"))
        self.assertEqual(resp_xlsx.status_code, 200)
        self.assertIn("spreadsheetml", resp_xlsx["Content-Type"])

        resp_pdf = self.client.get(reverse("reports:export_pdf"))
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf["Content-Type"], "application/pdf")

    def test_student_forbidden_from_reports(self):
        self.client.force_login(self.student_user)
        resp = self.client.get(reverse("reports:dashboard"))
        self.assertEqual(resp.status_code, 403)