from django.urls import path
from . import views

app_name = "finance"

urlpatterns = [
    path("", views.finance_dashboard, name="dashboard"),
    path("pay/<int:invoice_id>/", views.gateway_checkout, name="checkout"),
    path("receipt/<int:payment_id>/", views.download_receipt, name="receipt"),
    path("coordinator/", views.coordinator_finance, name="coordinator_list"),
    path("coordinator/<int:invoice_id>/cancel/", views.cancel_invoice, name="cancel_invoice"),
]