from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from documents.models import Document
from notifications.models import Notification
from users.models import EmployerProfile, LanguageLevel, StudentProfile
from vacancies.models import ActivityField, Country, Vacancy
from .models import Application, VisaStage

User = get_user_model()


class ApplicationsModuleTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="Германия", code="DE")
        self.field = ActivityField.objects.create(name="Гастрономия")

        self.emp_user = User.objects.create_user(
            username="emp_app", email="emp_app@example.com", password="Password123!", role=User.Role.EMPLOYER
        )
        self.employer = EmployerProfile.objects.create(
            user=self.emp_user,
            company_name="Karls GmbH",
            country="Германия",
            contact_person="Hans",
            phone="+491512345678",
            is_verified=True,
        )
        self.vac_b1 = Vacancy.objects.create(
            employer=self.employer,
            title="Повар",
            description="Работа летом",
            country=self.country,
            activity_field=self.field,
            salary_per_hour=Decimal("14.00"),
            min_language_level=LanguageLevel.B1,
            spots_count=4,
            available_from=date.today() + timedelta(days=200),
            available_to=date.today() + timedelta(days=260),
            is_active=True,
        )

        self.st_a2_user = User.objects.create_user(
            username="st_a2", email="st_a2@example.com", password="Password123!", role=User.Role.STUDENT
        )
        self.st_a2 = StudentProfile.objects.create(
            user=self.st_a2_user,
            first_name="Алия",
            last_name="Иванова",
            birth_date=date(2005, 5, 5),
            university="КГТУ",
            field_of_study="ПИ",
            course=3,
            language_level=LanguageLevel.A2,
            available_from=date.today() + timedelta(days=190),
            available_to=date.today() + timedelta(days=270),
            is_verified=True,
        )
        Document.objects.create(
            student=self.st_a2,
            doc_type=Document.DocType.PASSPORT,
            file=SimpleUploadedFile("p.pdf", b"%PDF-1.4", content_type="application/pdf"),
            status=Document.Status.VERIFIED,
        )

        self.st_b1_user = User.objects.create_user(
            username="st_b1", email="st_b1@example.com", password="Password123!", role=User.Role.STUDENT
        )
        self.st_b1 = StudentProfile.objects.create(
            user=self.st_b1_user,
            first_name="Айгерим",
            last_name="Халбекова",
            birth_date=date(2006, 2, 25),
            university="КГТУ",
            field_of_study="ПИ",
            course=3,
            language_level=LanguageLevel.B1,
            available_from=date.today() + timedelta(days=190),
            available_to=date.today() + timedelta(days=270),
            is_verified=True,
        )
        Document.objects.create(
            student=self.st_b1,
            doc_type=Document.DocType.PASSPORT,
            file=SimpleUploadedFile("p2.pdf", b"%PDF-1.4", content_type="application/pdf"),
            status=Document.Status.VERIFIED,
        )

        self.coord_user = User.objects.create_user(
            username="coord_app", email="coord_app@example.com", password="Password123!", role=User.Role.COORDINATOR
        )

    def test_block_apply_when_language_lower_than_required(self):
        self.client.force_login(self.st_a2_user)
        resp = self.client.post(
            reverse("applications:apply", args=[self.vac_b1.pk]),
            {"accept_terms": "on", "cover_letter": "Хочу работать"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Application.objects.count(), 0)

    def test_apply_job_offer_and_visa_progress(self):
        self.client.force_login(self.st_b1_user)
        resp = self.client.post(
            reverse("applications:apply", args=[self.vac_b1.pk]),
            {"accept_terms": "on", "cover_letter": "Готов к работе"},
        )
        self.assertEqual(resp.status_code, 302)
        app = Application.objects.get(student=self.st_b1, vacancy=self.vac_b1)
        self.assertEqual(app.status, Application.Status.REVIEWING)
        self.assertTrue(Notification.objects.filter(recipient=self.emp_user).exists())

        self.client.force_login(self.emp_user)
        resp2 = self.client.post(
            reverse("applications:decide", args=[app.pk]),
            {"action": "APPROVED", "job_offer_terms": "14 EUR/час, смены по графику"},
        )
        self.assertEqual(resp2.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.offer_status, Application.OfferStatus.SENT)

        self.client.force_login(self.st_b1_user)
        resp3 = self.client.post(
            reverse("applications:offer_response", args=[app.pk]),
            {"decision": "ACCEPT"},
        )
        self.assertEqual(resp3.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.offer_status, Application.OfferStatus.ACCEPTED)

        self.client.force_login(self.coord_user)
        resp4 = self.client.post(
            reverse("applications:update_visa", args=[app.pk]),
            {"stage": VisaStage.Stage.UNDER_REVIEW, "authority_note": "Документы в ZAV"},
        )
        self.assertEqual(resp4.status_code, 302)
        visa = VisaStage.objects.get(application=app)
        self.assertEqual(visa.progress_percent, 55)