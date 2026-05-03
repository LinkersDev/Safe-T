"""Read-only queries for the payments app."""
from django.db.models import QuerySet

from .models import BillProvider, MerchantProfile, QRPayment


def get_merchant_by_user(user) -> MerchantProfile | None:
    return (
        MerchantProfile.objects.filter(user=user)
        .select_related("settlement_account", "user")
        .first()
    )


def get_active_bill_providers(service_type: str | None = None) -> QuerySet:
    qs = BillProvider.objects.filter(is_active=True).order_by("service_type", "name")
    if service_type:
        qs = qs.filter(service_type=service_type)
    return qs


def get_qr_payments_for_merchant(merchant_profile: MerchantProfile) -> QuerySet:
    return (
        QRPayment.objects.filter(merchant_profile=merchant_profile)
        .select_related("transaction", "payer_account")
        .order_by("-created_at")
    )


def get_qr_payment_by_token(token: str) -> QRPayment | None:
    return (
        QRPayment.objects.filter(qr_token=token)
        .select_related("merchant_profile", "merchant_account", "currency")
        .first()
    )
