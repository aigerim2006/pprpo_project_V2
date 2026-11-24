"""Представления новостной ленты и её администрирования координатором (FR-3.7, UC-18)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import NewsForm
from .models import News


def news_list(request):
    items = News.for_user(request.user)
    return render(request, "news/news_list.html", {"news_items": items})


@login_required
def news_create(request):
    if not request.user.is_coordinator:
        raise PermissionDenied
    if request.method == "POST":
        form = NewsForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.author = request.user
            item.save()
            messages.success(request, _("Публикация добавлена в новостную ленту."))
            return redirect("news:list")
    else:
        form = NewsForm()
    return render(request, "news/news_form.html", {"form": form, "is_edit": False})


@login_required
def news_edit(request, pk):
    if not request.user.is_coordinator:
        raise PermissionDenied
    item = get_object_or_404(News, pk=pk)
    if request.method == "POST":
        form = NewsForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, _("Новость обновлена."))
            return redirect("news:list")
    else:
        form = NewsForm(instance=item)
    return render(request, "news/news_form.html", {"form": form, "item": item, "is_edit": True})


@login_required
@require_POST
def news_delete(request, pk):
    if not request.user.is_coordinator:
        raise PermissionDenied
    item = get_object_or_404(News, pk=pk)
    item.delete()
    messages.info(request, _("Публикация удалена."))
    return redirect("news:list")