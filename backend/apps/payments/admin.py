"""Django admin registrations for payments models."""
from django.contrib import admin

from .models import BillPayment, BillProvider, MerchantProfile, QRPayment


@admin.register(MerchantProfile)
class MerchantProfileAdmin(admin.ModelAdmin):
    list_display = ("business_name", "user", "registration_number", "status", "created_at")
    list_filter = ("status", "business_type")
    search_fields = ("business_name", "registration_number", "user__phone_number")
    readonly_fields = ("created_at", "updated_at")


@admin.register(QRPayment)
class QRPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "qr_token_short", "merchant_profile", "amount_mode",
        "display_amount", "status", "expires_at", "created_at",
    )
    list_filter = ("status", "amount_mode")
    search_fields = ("qr_token", "merchant_profile__business_name")
    readonly_fields = (
        "qr_token", "qr_payload_hash", "merchant_profile", "merchant_account",
        "payer_account", "transaction", "scanned_at", "created_at",
    )

    def qr_token_short(self, obj):
        return obj.qr_token[:16] + "…"
    qr_token_short.short_description = "QR Token"


@admin.register(BillProvider)
class BillProviderAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "service_type", "is_active", "created_at")
    list_filter = ("service_type", "is_active")
    search_fields = ("code", "name")


@admin.register(BillPayment)
class BillPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "bill_provider", "service_number", "biller_amount",
        "fee_amount", "paid_at", "created_at",
    )
    list_filter = ("bill_provider",)
    search_fields = ("service_number", "bill_reference")
    readonly_fields = (
        "transaction", "bill_provider", "payer_account",
        "service_number", "bill_reference", "biller_amount", "fee_amount",
        "fetched_at", "paid_at", "created_at",
    )
