from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import News

User = get_user_model()


class NewsModuleTests(TestCase):
    def setUp(self):
        self.coord = User.objects.create_user(
            username="coord_news", email="coord_news@example.com", password="Password123!", role=User.Role.COORDINATOR
        )
        self.student = User.objects.create_user(
            username="st_news", email="st_news@example.com", password="Password123!", role=User.Role.STUDENT
        )
        self.employer = User.objects.create_user(
            username="emp_news", email="emp_news@example.com", password="Password123!", role=User.Role.EMPLOYER
        )
        News.objects.create(title="Для студентов", content="Текст 1", audience=News.Audience.STUDENT)
        News.objects.create(title="Для компаний", content="Текст 2", audience=News.Audience.EMPLOYER)
        News.objects.create(title="Общая новость", content="Текст 3", audience=News.Audience.ALL)

    def test_audience_filtering(self):
        self.client.force_login(self.student)
        resp = self.client.get(reverse("news:list"))
        self.assertContains(resp, "Для студентов")
        self.assertContains(resp, "Общая новость")
        self.assertNotContains(resp, "Для компаний")

        self.client.force_login(self.employer)
        resp_emp = self.client.get(reverse("news:list"))
        self.assertContains(resp_emp, "Для компаний")
        self.assertNotContains(resp_emp, "Для студентов")