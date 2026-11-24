"""Сервисные функции создания и рассылки внутренних уведомлений."""
from django.contrib.auth import get_user_model
from .models import Notification


def notify_user(recipient, title, message, link=""):
    if not recipient:
        return None
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        link=link,
    )


def notify_coordinators(title, message, link=""):
    User = get_user_model()
    coordinators = User.objects.filter(role=User.Role.COORDINATOR, is_active=True)
    notifications = [
        Notification(recipient=coord, title=title, message=message, link=link)
        for coord in coordinators
    ]
    if notifications:
        return Notification.objects.bulk_create(notifications)
    return []