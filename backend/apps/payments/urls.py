"""Customer-facing payment URL patterns (prefix: /api/payments/)."""
from django.urls import path

from . import views

urlpatterns = [
    # Transfer
    path("transfer/recipient/", views.transfer_recipient_lookup, name="payment-transfer-recipient"),
    path("transfer/otp/", views.transfer_otp, name="payment-transfer-otp"),
    path("transfer/", views.transfer_execute, name="payment-transfer-execute"),
    path("p2p-receive-qr/issue/", views.p2p_receive_qr_issue, name="payment-p2p-receive-qr-issue"),
    path("p2p-receive-qr/resolve/", views.p2p_receive_qr_resolve, name="payment-p2p-receive-qr-resolve"),
    # QR
    path("qr/otp/", views.qr_pay_otp, name="payment-qr-otp"),
    path("qr/pay/", views.qr_pay_execute, name="payment-qr-execute"),
    path("qr/<str:qr_token>/", views.qr_resolve, name="payment-qr-resolve"),
    # Bill
    path("bill/providers/", views.bill_provider_list, name="payment-bill-providers"),
    path("bill/fetch/", views.bill_fetch, name="payment-bill-fetch"),
    path("bill/otp/", views.bill_pay_otp, name="payment-bill-otp"),
    path("bill/pay/", views.bill_pay_execute, name="payment-bill-execute"),
]
