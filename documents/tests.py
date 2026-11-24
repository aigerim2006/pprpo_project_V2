from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from notifications.models import Notification
from users.models import LanguageLevel, StudentProfile
from .models import Document

User = get_user_model()


class DocumentsModuleTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            username="student_doc",
            email="st_doc@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            first_name="Айгерим",
            last_name="Халбекова",
            birth_date=date(2005, 1, 1),
            university="КГТУ",
            field_of_study="ПИ",
            course=3,
            language_level=LanguageLevel.B1,
            available_from=date.today(),
            available_to=date.today() + timedelta(days=60),
        )
        self.coord_user = User.objects.create_user(
            username="coord_doc",
            email="coord_doc@example.com",
            password="Password123!",
            role=User.Role.COORDINATOR,
        )

    def test_upload_valid_pdf_and_notify_coordinator(self):
        self.client.force_login(self.student_user)
        pdf_file = SimpleUploadedFile("passport.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
        resp = self.client.post(
            reverse("documents:upload"),
            {
                "doc_type": Document.DocType.PASSPORT,
                "file": pdf_file,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Document.objects.filter(student=self.student, status=Document.Status.PENDING).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.coord_user).count(), 1)

    def test_reject_disallowed_extension_exe(self):
        self.client.force_login(self.student_user)
        exe_file = SimpleUploadedFile("virus.exe", b"MZ...", content_type="application/octet-stream")
        resp = self.client.post(
            reverse("documents:upload"),
            {
                "doc_type": Document.DocType.CV,
                "file": exe_file,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Document.objects.count(), 0)

    def test_coordinator_verify_document_and_student(self):
        doc = Document.objects.create(
            student=self.student,
            doc_type=Document.DocType.STUDY_CERT,
            file=SimpleUploadedFile("cert.pdf", b"%PDF-1.4 cert", content_type="application/pdf"),
        )
        self.client.force_login(self.coord_user)
        resp = self.client.post(
            reverse("documents:review", args=[doc.pk]),
            {"decision": "VERIFY"},
        )
        self.assertEqual(resp.status_code, 302)
        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.VERIFIED)

        resp2 = self.client.post(reverse("documents:toggle_student_verify", args=[self.student.pk]))
        self.assertEqual(resp2.status_code, 302)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_verified)