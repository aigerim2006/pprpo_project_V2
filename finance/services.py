"""Сервис генерации электронной PDF-квитанции об оплате (UC-15, UC-19)."""
from io import BytesIO
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def _register_cyrillic_font():
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", path))
                return "DejaVuSans"
            except Exception:
                pass
    return "Helvetica"


def generate_payment_receipt_pdf(payment):
    """Формирует PDF-квитанцию и сохраняет её в payment.receipt_pdf."""
    font_name = _register_cyrillic_font()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    invoice = payment.invoice
    student = invoice.student

    y = height - 60
    pdf.setFont(font_name, 14)
    pdf.drawString(50, y, "АИС ЗСТС — ЭЛЕКТРОННАЯ КВИТАНЦИЯ ОБ ОПЛАТЕ")
    y -= 22
    pdf.setFont(font_name, 10)
    pdf.drawString(50, y, "КГТУ им. И. Раззакова | Автоматизированная информационная система")
    y -= 18
    pdf.line(50, y, width - 50, y)
    y -= 28

    lines = [
        f"Номер транзакции: {payment.transaction_id}",
        f"Номер счёта: {invoice.number}",
        f"Дата и время оплаты: {timezone.localtime(payment.created_at).strftime('%d.%m.%Y %H:%M')}",
        f"Плательщик (студент): {student.get_full_name()} ({student.university})",
        f"Назначение платежа: {invoice.get_service_type_display()} — {invoice.description}",
        f"Оплаченная сумма: {payment.amount} EUR",
        f"Способ оплаты: Банковская карта (**** {payment.card_last4 or '0000'})",
        f"Всего оплачено по счёту: {invoice.amount_paid} EUR из {invoice.amount_total} EUR",
        f"Остаток задолженности: {invoice.balance_due} EUR",
        f"Статус транзакции: {payment.get_status_display()}",
    ]

    for line in lines:
        pdf.drawString(50, y, line)
        y -= 22

    y -= 14
    pdf.line(50, y, width - 50, y)
    y -= 22
    pdf.setFont(font_name, 9)
    pdf.drawString(50, y, f"Сформировано автоматически в АИС ЗСТС ({getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ais-zsts.local')}).")

    pdf.showPage()
    pdf.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()
    filename = f"receipt_{payment.transaction_id}.pdf"
    payment.receipt_pdf.save(filename, ContentFile(pdf_bytes), save=True)
    return payment.receipt_pdf