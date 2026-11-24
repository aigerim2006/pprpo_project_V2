"""Smoke-тесты модуля users (ТЗ, п. 7.1, тесты №1–2) и контроль доступа."""
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from .models import EmployerProfile, StudentProfile, User

PASSWORD = "Str0ng-Pass!2026"


def student_data(**overrides):
    data = {
        "username": "aigerim",
        "email": "aigerim@example.com",
        "password1": PASSWORD,
        "password2": PASSWORD,
        "first_name": "Айгерим",
        "last_name": "Халбекова",
        "birth_date": "2004-05-10",
        "university": "КГТУ им. И. Раззакова",
        "field_of_study": "Программное обеспечение компьютерных систем",
        "course": 2,
        "language_level": "B1",
        "available_from": "2027-06-01",
        "available_to": "2027-09-15",
        "is_full_time": "on",
    }
    data.update(overrides)
    return data


def employer_data(**overrides):
    data = {
        "username": "bauer",
        "email": "hr@bauer.example.com",
        "password1": PASSWORD,
        "password2": PASSWORD,
        "company_name": "Bauer Farm GmbH",
        "country": "Германия",
        "contact_person": "Hans Bauer",
        "phone": "+49 151 1234567",
    }
    data.update(overrides)
    return data


class RegistrationTests(TestCase):
    def test_student_registration_creates_user_and_profile(self):
        response = self.client.post(reverse("users:register_student"), student_data())
        self.assertRedirects(response, reverse("users:dashboard"))
        user = User.objects.get(username="aigerim")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        profile = StudentProfile.objects.get(user=user)
        self.assertFalse(profile.is_verified)
        self.assertEqual(profile.get_full_name(), "Айгерим Халбекова")

    def test_underage_student_is_rejected(self):
        born = date.today() - timedelta(days=17 * 365)
        response = self.client.post(
            reverse("users:register_student"), student_data(birth_date=born.isoformat())
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="aigerim").exists())

    def test_full_time_confirmation_is_required(self):
        data = student_data()
        del data["is_full_time"]
        response = self.client.post(reverse("users:register_student"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="aigerim").exists())

    def test_employer_registration_awaits_verification(self):
        response = self.client.post(reverse("users:register_employer"), employer_data())
        self.assertRedirects(response, reverse("users:dashboard"))
        profile = EmployerProfile.objects.get(user__username="bauer")
        self.assertFalse(profile.is_verified)


class LoginTests(TestCase):
    def test_wrong_password_shows_error(self):
        User.objects.create_user("aigerim", "a@example.com", PASSWORD)
        response = self.client.post(
            reverse("users:login"), {"username": "aigerim", "password": "wrong"}
        )
        self.assertContains(response, "Неверный логин или пароль")


class CoordinatorAccessTests(TestCase):
    def setUp(self):
        self.coordinator = User.objects.create_user(
            "coord", "coord@example.com", PASSWORD, role=User.Role.COORDINATOR
        )
        self.student = User.objects.create_user("stud", "s@example.com", PASSWORD)
        employer = User.objects.create_user(
            "emp", "e@example.com", PASSWORD, role=User.Role.EMPLOYER
        )
        self.employer_profile = EmployerProfile.objects.create(
            user=employer,
            company_name="Test GmbH",
            country="Германия",
            contact_person="Max",
            phone="+49 30 123456",
        )

    def test_coordinator_is_staff(self):
        self.assertTrue(self.coordinator.is_staff)
        self.assertFalse(self.student.is_staff)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse("users:coordinator_users"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response.url)

    def test_student_gets_403(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("users:coordinator_users"))
        self.assertEqual(response.status_code, 403)

    def test_coordinator_verifies_employer(self):
        self.client.force_login(self.coordinator)
        url = reverse("users:employer_verify", args=[self.employer_profile.user_id])
        self.client.post(url)
        self.employer_profile.refresh_from_db()
        self.assertTrue(self.employer_profile.is_verified)

    def test_coordinator_cannot_deactivate_self(self):
        self.client.force_login(self.coordinator)
        self.client.post(reverse("users:user_toggle_active", args=[self.coordinator.pk]))
        self.coordinator.refresh_from_db()
        self.assertTrue(self.coordinator.is_active)
