from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.models import LanguageLevel, StudentProfile
from .models import Invoice, Payment

User = get_user_model()


class FinanceModuleTests(TestCase):
    def setUp(self):
        self.coord = User.objects.create_user(
            username="coord_fin", email="coord_fin@example.com", password="Password123!", role=User.Role.COORDINATOR
        )
        self.st_user = User.objects.create_user(
            username="st_fin", email="st_fin@example.com", password="Password123!", role=User.Role.STUDENT
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
            available_from=date(2026, 6, 1),
            available_to=date(2026, 9, 1),
            is_verified=True,
        )
        self.invoice = Invoice.objects.create(
            student=self.student,
            service_type=Invoice.ServiceType.CONTRACT,
            description="Контракт Ferienjob",
            amount_total=Decimal("300.00"),
            created_by=self.coord,
        )

    def test_payment_gateway_success_updates_balance_and_generates_pdf(self):
        self.client.force_login(self.st_user)
        resp = self.client.post(
            reverse("finance:checkout", args=[self.invoice.pk]),
            {
                "amount": "200.00",
                "card_holder": "AIGERIM KHALBEKOVA",
                "card_number": "4169580012345678",
                "expiry": "08/28",
                "cvv": "123",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal("200.00"))
        self.assertEqual(self.invoice.balance_due, Decimal("100.00"))
        self.assertEqual(self.invoice.status, Invoice.Status.PARTIAL)

        payment = Payment.objects.get(invoice=self.invoice)
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
        self.assertTrue(bool(payment.receipt_pdf))

        pdf_resp = self.client.get(reverse("finance:receipt", args=[payment.pk]))
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp["Content-Type"], "application/pdf")

    def test_payment_gateway_declined_card(self):
        self.client.force_login(self.st_user)
        resp = self.client.post(
            reverse("finance:checkout", args=[self.invoice.pk]),
            {
                "amount": "300.00",
                "card_holder": "AIGERIM KHALBEKOVA",
                "card_number": "4169580012340000",
                "expiry": "08/28",
                "cvv": "123",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal("0.00"))
        self.assertEqual(self.invoice.status, Invoice.Status.UNPAID)
        self.assertEqual(Payment.objects.filter(status=Payment.Status.FAILED).count(), 1)