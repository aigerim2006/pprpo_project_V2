"""Сервисные функции создания внутренних уведомлений и отправки писем (FR-1.7, SMTP)."""
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger(__name__)


def _send_email_safe(recipient, title, message):
    if not recipient or not getattr(recipient, "email", ""):
        return
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@ais-zsts.local")
    try:
        send_mail(
            subject=title,
            message=message,
            from_email=from_email,
            recipient_list=[recipient.email],
            fail_silently=True,
        )
    except Exception as exc:
        logger.warning("Ошибка отправки email получателю %s: %s", recipient.email, exc)


def notify_user(recipient, title, message, link="", send_email=True):
    if not recipient:
        return None
    notif = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        link=link,
    )
    if send_email:
        _send_email_safe(recipient, title, message)
    return notif


def notify_coordinators(title, message, link="", send_email=True):
    User = get_user_model()
    coordinators = list(User.objects.filter(role=User.Role.COORDINATOR, is_active=True))
    notifications = [
        Notification(recipient=coord, title=title, message=message, link=link)
        for coord in coordinators
    ]
    created = Notification.objects.bulk_create(notifications) if notifications else []
    if send_email:
        for coord in coordinators:
            _send_email_safe(coord, title, message)
    return created