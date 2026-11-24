"""Общие представления проекта: главная страница и обработчики ошибок."""
from django.http import HttpResponseServerError
from django.shortcuts import render
from django.template import loader


def home(request):
    return render(request, "home.html")


def error_403(request, exception=None):
    return render(request, "403.html", status=403)


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    # Без контекста запроса: страница должна открыться даже при сбое БД/сессий.
    return HttpResponseServerError(loader.get_template("500.html").render())
