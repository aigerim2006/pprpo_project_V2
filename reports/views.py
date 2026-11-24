"""Представления сводных отчётов и экспорта Excel/PDF для координатора (FR-3.4)."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render

from .forms import ReportFilterForm
from .services import (
    export_report_excel,
    export_report_pdf,
    get_report_rows,
    get_summary_metrics,
)


@login_required
def report_dashboard(request):
    if not request.user.is_coordinator:
        raise PermissionDenied

    form = ReportFilterForm(request.GET or None)
    country_id = request.GET.get("country", "")
    status = request.GET.get("status", "")

    rows = get_report_rows(country_id=country_id, status=status)
    metrics = get_summary_metrics(rows)

    return render(
        request,
        "reports/report_dashboard.html",
        {
            "form": form,
            "rows": rows,
            "metrics": metrics,
        },
    )


@login_required
def export_excel(request):
    if not request.user.is_coordinator:
        raise PermissionDenied
    rows = get_report_rows(
        country_id=request.GET.get("country", ""),
        status=request.GET.get("status", ""),
    )
    data = export_report_excel(rows)
    response = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="ais_zsts_report.xlsx"'
    return response


@login_required
def export_pdf(request):
    if not request.user.is_coordinator:
        raise PermissionDenied
    rows = get_report_rows(
        country_id=request.GET.get("country", ""),
        status=request.GET.get("status", ""),
    )
    data = export_report_pdf(rows)
    response = HttpResponse(data, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="ais_zsts_report.pdf"'
    return response