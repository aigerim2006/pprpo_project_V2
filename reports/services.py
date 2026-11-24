"""Сервисы формирования сводных отчётов с кэшированием и экспортом в Excel/PDF (FR-3.4, п. 2.2.4)."""
from io import BytesIO
import os

from django.core.cache import cache
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from applications.models import Application, VisaStage
from finance.models import Invoice


def get_report_rows(country_id="", status=""):
    cache_key = f"ais_zsts_report_rows:{country_id or 'all'}:{status or 'all'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs = Application.objects.select_related(
        "student",
        "student__user",
        "vacancy",
        "vacancy__country",
        "vacancy__employer",
        "visa_stage",
    ).order_by("-applied_at")

    if str(country_id).isdigit():
        qs = qs.filter(vacancy__country_id=int(country_id))
    if status:
        qs = qs.filter(status=status)

    rows = []
    for app in qs:
        visa = getattr(app, "visa_stage", None)
        rows.append(
            {
                "id": app.pk,
                "student_name": app.student.get_full_name(),
                "university": app.student.university,
                "course": app.student.course,
                "language_level": app.student.language_level,
                "employer": app.vacancy.employer.company_name,
                "vacancy": app.vacancy.title,
                "country": app.vacancy.country.name,
                "status": app.get_status_display(),
                "offer_status": app.get_offer_status_display(),
                "visa_stage": visa.get_stage_display() if visa else "Не начато",
                "visa_progress": visa.progress_percent if visa else 0,
                "applied_at": timezone.localtime(app.applied_at).strftime("%d.%m.%Y"),
            }
        )

    cache.set(cache_key, rows, timeout=300)
    return rows


def get_summary_metrics(rows):
    total = len(rows)
    approved = sum(1 for r in rows if r["status"] in ("Одобрена", "Завершена / Опыт пройден"))
    visas_issued = sum(1 for r in rows if r["visa_progress"] == 100)
    invoices_count = Invoice.objects.count()
    return {
        "total": total,
        "approved": approved,
        "visas_issued": visas_issued,
        "invoices_count": invoices_count,
    }


def export_report_excel(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Трудоустройство студентов"

    headers = [
        "№",
        "ФИО студента",
        "ВУЗ",
        "Курс",
        "Язык",
        "Работодатель",
        "Вакансия",
        "Страна",
        "Статус заявки",
        "Job Offer",
        "Визовый этап",
        "Прогресс (%)",
        "Дата отклика",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for idx, r in enumerate(rows, start=1):
        ws.append(
            [
                idx,
                r["student_name"],
                r["university"],
                r["course"],
                r["language_level"],
                r["employer"],
                r["vacancy"],
                r["country"],
                r["status"],
                r["offer_status"],
                r["visa_stage"],
                r["visa_progress"],
                r["applied_at"],
            ]
        )

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _register_font():
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ):
        if os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", path))
                return "DejaVuSans"
            except Exception:
                pass
    return "Helvetica"


def export_report_pdf(rows):
    font_name = _register_font()
    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=landscape(A4))
    width, height = landscape(A4)

    y = height - 40
    pdf.setFont(font_name, 13)
    pdf.drawString(40, y, "АИС ЗСТС — Сводный отчёт по трудоустройству студентов")
    y -= 18
    pdf.setFont(font_name, 9)
    pdf.drawString(
        40,
        y,
        f"Дата формирования: {timezone.localtime(timezone.now()).strftime('%d.%m.%Y %H:%M')} | Всего записей: {len(rows)}",
    )
    y -= 22

    headers = ["№", "Студент", "ВУЗ", "Страна", "Работодатель / Вакансия", "Статус", "Виза (%)"]
    xs = [40, 65, 220, 350, 440, 640, 745]
    pdf.setFont(font_name, 9)
    for x, title in zip(xs, headers):
        pdf.drawString(x, y, title)
    y -= 8
    pdf.line(40, y, width - 40, y)
    y -= 16

    for idx, r in enumerate(rows, start=1):
        if y < 50:
            pdf.showPage()
            y = height - 45
            pdf.setFont(font_name, 9)
        vals = [
            str(idx),
            r["student_name"][:24],
            r["university"][:20],
            r["country"][:14],
            f"{r['employer']} — {r['vacancy']}"[:30],
            r["status"][:16],
            f"{r['visa_stage'][:14]} ({r['visa_progress']}%)",
        ]
        for x, val in zip(xs, vals):
            pdf.drawString(x, y, val)
        y -= 16

    pdf.showPage()
    pdf.save()
    return buf.getvalue()