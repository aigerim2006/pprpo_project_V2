"""Представления модуля финансов: оплата услуг, шлюз, PDF-квитанции, контроль координатора."""
from decimal import Decimal
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from notifications.services import notify_coordinators, notify_user
from .forms import InvoiceCreateForm, PaymentGatewayForm
from .models import Invoice, Payment
from .services import generate_payment_receipt_pdf


@login_required
def finance_dashboard(request):
    if request.user.is_coordinator:
        return redirect("finance:coordinator_list")
    if not request.user.is_student:
        raise PermissionDenied

    student = getattr(request.user, "student_profile", None)
    invoices = (
        Invoice.objects.filter(student=student).prefetch_related("payments")
        if student
        else Invoice.objects.none()
    )
    payments = (
        Payment.objects.filter(invoice__student=student).select_related("invoice")
        if student
        else Payment.objects.none()
    )

    total_billed = sum((inv.amount_total for inv in invoices if inv.status != Invoice.Status.CANCELLED), Decimal("0.00"))
    total_paid = sum((inv.amount_paid for inv in invoices if inv.status != Invoice.Status.CANCELLED), Decimal("0.00"))
    total_debt = sum((inv.balance_due for inv in invoices if inv.status != Invoice.Status.CANCELLED), Decimal("0.00"))

    return render(
        request,
        "finance/student_finance.html",
        {
            "invoices": invoices,
            "payments": payments,
            "total_billed": total_billed,
            "total_paid": total_paid,
            "total_debt": total_debt,
        },
    )


@login_required
def gateway_checkout(request, invoice_id):
    if not request.user.is_student:
        raise PermissionDenied
    student = getattr(request.user, "student_profile", None)
    invoice = get_object_or_404(Invoice, pk=invoice_id, student=student)

    if invoice.status in (Invoice.Status.PAID, Invoice.Status.CANCELLED) or invoice.balance_due <= Decimal("0.00"):
        messages.info(request, _("Данный счёт уже полностью оплачен или отменён."))
        return redirect("finance:dashboard")

    if request.method == "POST":
        form = PaymentGatewayForm(request.POST, max_amount=invoice.balance_due)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            card_digits = form.cleaned_data["card_number"]
            cvv = form.cleaned_data["cvv"]

            # Имитация ответа банковского шлюза по сценарию 5а UC-15 (отказ по карте *0000 или CVV 000)
            if card_digits.endswith("0000") or cvv == "000":
                Payment.objects.create(
                    invoice=invoice,
                    amount=amount,
                    card_last4=card_digits[-4:],
                    status=Payment.Status.FAILED,
                    failure_reason=_("Транзакция отклонена банком (недостаточно средств или неверный CVV)."),
                )
                messages.error(
                    request,
                    _("Ошибка оплаты: транзакция отклонена банком. Повторите попытку или используйте другую карту."),
                )
                return redirect("finance:checkout", invoice_id=invoice.pk)

            with transaction.atomic():
                payment = Payment.objects.create(
                    invoice=invoice,
                    amount=amount,
                    card_last4=card_digits[-4:],
                    status=Payment.Status.SUCCEEDED,
                )
                invoice.recalculate_balance()
                generate_payment_receipt_pdf(payment)

            notify_user(
                recipient=request.user,
                title=_("Платёж успешно проведён"),
                message=_("Оплата %(amt)s EUR по счёту %(num)s подтверждена. Остаток долга: %(bal)s EUR.")
                % {"amt": payment.amount, "num": invoice.number, "bal": invoice.balance_due},
                link="/finance/",
            )
            notify_coordinators(
                title=_("Поступила оплата от студента"),
                message=_("Студент %(st)s оплатил %(amt)s EUR по счёту %(num)s.")
                % {"st": student.get_full_name(), "amt": payment.amount, "num": invoice.number},
                link="/finance/coordinator/",
            )
            messages.success(request, _("Оплата успешно проведена. Электронная квитанция сформирована."))
            return redirect("finance:dashboard")
    else:
        form = PaymentGatewayForm(max_amount=invoice.balance_due)

    return render(
        request,
        "finance/gateway_checkout.html",
        {"invoice": invoice, "form": form},
    )


@login_required
def download_receipt(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related("invoice", "invoice__student"), pk=payment_id
    )
    allowed = request.user.is_coordinator or (
        request.user.is_student
        and getattr(request.user, "student_profile", None) == payment.invoice.student
    )
    if not allowed or payment.status != Payment.Status.SUCCEEDED:
        raise PermissionDenied

    if not payment.receipt_pdf or not os.path.isfile(payment.receipt_pdf.path):
        generate_payment_receipt_pdf(payment)

    if not payment.receipt_pdf or not os.path.isfile(payment.receipt_pdf.path):
        raise Http404(_("Квитанция не найдена."))

    return FileResponse(
        open(payment.receipt_pdf.path, "rb"),
        as_attachment=True,
        filename=os.path.basename(payment.receipt_pdf.name),
    )


@login_required
def coordinator_finance(request):
    if not request.user.is_coordinator:
        raise PermissionDenied

    if request.method == "POST":
        form = InvoiceCreateForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            invoice.save()
            notify_user(
                recipient=invoice.student.user,
                title=_("Выставлен новый счёт на оплату"),
                message=_("Счёт %(num)s на сумму %(amt)s EUR: %(desc)s.")
                % {"num": invoice.number, "amt": invoice.amount_total, "desc": invoice.description},
                link="/finance/",
            )
            messages.success(request, _("Счёт %(num)s выставлен студенту.") % {"num": invoice.number})
            return redirect("finance:coordinator_list")
    else:
        form = InvoiceCreateForm()

    invoices = Invoice.objects.select_related("student", "student__user", "application").all()
    payments = Payment.objects.select_related("invoice", "invoice__student").all()[:30]

    agg = invoices.exclude(status=Invoice.Status.CANCELLED).aggregate(
        billed=Sum("amount_total"), paid=Sum("amount_paid")
    )
    total_billed = agg["billed"] or Decimal("0.00")
    total_paid = agg["paid"] or Decimal("0.00")
    total_debt = max(total_billed - total_paid, Decimal("0.00"))

    return render(
        request,
        "finance/coordinator_finance.html",
        {
            "form": form,
            "invoices": invoices,
            "payments": payments,
            "total_billed": total_billed,
            "total_paid": total_paid,
            "total_debt": total_debt,
        },
    )


@login_required
@require_POST
def cancel_invoice(request, invoice_id):
    if not request.user.is_coordinator:
        raise PermissionDenied
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    if invoice.amount_paid == Decimal("0.00"):
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=["status", "updated_at"])
        messages.info(request, _("Счёт отменён."))
    else:
        messages.error(request, _("Нельзя отменить счёт, по которому уже внесена оплата."))
    return redirect("finance:coordinator_list")