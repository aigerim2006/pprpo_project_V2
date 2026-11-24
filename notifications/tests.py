from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Notification
from .services import notify_coordinators, notify_user

User = get_user_model()


class NotificationTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="st1", email="st1@example.com", password="Password123!", role=User.Role.STUDENT
        )
        self.coord = User.objects.create_user(
            username="coord1", email="c1@example.com", password="Password123!", role=User.Role.COORDINATOR
        )

    def test_notify_user_and_mark_read(self):
        notif = notify_user(self.student, "Тест", "Сообщение", "/documents/")
        self.assertEqual(Notification.objects.filter(recipient=self.student, is_read=False).count(), 1)
        self.client.force_login(self.student)
        resp = self.client.post(reverse("notifications:mark_read", args=[notif.pk]))
        self.assertEqual(resp.status_code, 302)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_notify_coordinators(self):
        notify_coordinators("Новый документ", "Студент загрузил скан")
        self.assertEqual(Notification.objects.filter(recipient=self.coord).count(), 1)