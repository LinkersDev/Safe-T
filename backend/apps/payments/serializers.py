"""DRF serializers for the payments app."""
from decimal import Decimal

from rest_framework import serializers

from apps.accounts.validators import validate_account_number
from apps.security.serializers import PhoneField

from .models import BillPayment, BillProvider, MerchantProfile, QRPayment


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------

class TransferOTPSerializer(serializers.Serializer):
    """Request an OTP before executing a transfer."""
    pass  # No fields — OTP is sent to the authenticated user's phone


class TransferExecuteSerializer(serializers.Serializer):
    destination_account_number = serializers.CharField(
        max_length=16,
        validators=[validate_account_number],
        required=False,
        allow_blank=True,
        default="",
    )
    destination_phone_number = PhoneField(required=False)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    currency_code = serializers.CharField(max_length=3, default="USD")
    pin = serializers.CharField(min_length=4, max_length=6, write_only=True)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_blank=True, default=None)
    source_account_number = serializers.CharField(
        max_length=16,
        required=False,
        validators=[validate_account_number],
        help_text="Defaults to the user's primary account if not specified.",
    )

    def validate_pin(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain digits only.")
        return value

    def validate(self, data: dict) -> dict:
        data = super().validate(data)
        has_account = bool(data.get("destination_account_number"))
        has_phone = bool(data.get("destination_phone_number"))
        if has_account == has_phone:
            raise serializers.ValidationError(
                "Provide exactly one of 'destination_account_number' or 'destination_phone_number'."
            )
        return data


# ---------------------------------------------------------------------------
# QR Payment
# ---------------------------------------------------------------------------

class QRGenerateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
        help_text="Leave null for OPEN amount mode.",
    )
    currency_code = serializers.CharField(max_length=3, default="USD")


class QRPayOTPSerializer(serializers.Serializer):
    qr_token = serializers.CharField(max_length=128)


class QRPayExecuteSerializer(serializers.Serializer):
    qr_token = serializers.CharField(max_length=128)
    otp_code = serializers.CharField(min_length=6, max_length=6)
    amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
        help_text="Required only for OPEN amount mode QR codes.",
    )
    source_account_number = serializers.CharField(max_length=16, validators=[validate_account_number])
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_blank=True, default=None)


class QRPaymentSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source="merchant_profile.business_name", read_only=True)
    currency_code = serializers.CharField(source="currency_id", read_only=True)

    class Meta:
        model = QRPayment
        fields = [
            "id",
            "qr_token",
            "merchant_name",
            "amount_mode",
            "display_amount",
            "currency_code",
            "status",
            "expires_at",
            "created_at",
        ]


# ---------------------------------------------------------------------------
# Bill Payment
# ---------------------------------------------------------------------------

class BillProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillProvider
        fields = ["code", "name", "service_type"]


class BillFetchSerializer(serializers.Serializer):
    provider_code = serializers.CharField(max_length=50)
    service_number = serializers.CharField(max_length=100)


class BillPayOTPSerializer(serializers.Serializer):
    provider_code = serializers.CharField(max_length=50)
    service_number = serializers.CharField(max_length=100)


class BillPayExecuteSerializer(serializers.Serializer):
    provider_code = serializers.CharField(max_length=50)
    service_number = serializers.CharField(max_length=100)
    bill_reference = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    otp_code = serializers.CharField(min_length=6, max_length=6)
    source_account_number = serializers.CharField(max_length=16, validators=[validate_account_number])
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_blank=True, default=None)


# ---------------------------------------------------------------------------
# Merchant
# ---------------------------------------------------------------------------

class MerchantProfileSerializer(serializers.ModelSerializer):
    settlement_account_number = serializers.CharField(
        source="settlement_account.account_number", read_only=True
    )

    class Meta:
        model = MerchantProfile
        fields = [
            "id",
            "business_name",
            "business_type",
            "registration_number",
            "contact_phone",
            "address",
            "status",
            "settlement_account_number",
            "created_at",
        ]
