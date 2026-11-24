"""Представления модуля внутренних уведомлений."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    items = Notification.objects.filter(recipient=request.user)
    unread_count = items.filter(is_read=False).count()
    return render(
        request,
        "notifications/notification_list.html",
        {"notifications": items, "unread_count": unread_count},
    )


@login_required
@require_POST
def mark_as_read(request, pk):
    item = get_object_or_404(Notification, pk=pk, recipient=request.user)
    item.is_read = True
    item.save(update_fields=["is_read"])
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_as_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")