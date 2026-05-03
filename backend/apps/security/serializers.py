"""
Security app request / response serializers.
"""
from __future__ import annotations

import phonenumbers
from rest_framework import serializers


# ---------------------------------------------------------------------------
# Reusable field
# ---------------------------------------------------------------------------

class PhoneField(serializers.CharField):
    """
    Validates and normalises phone numbers to E.164 format.
    Rejects numbers that cannot be parsed or are not valid.
    """

    def to_internal_value(self, data: str) -> str:
        value = super().to_internal_value(data)
        try:
            parsed = phonenumbers.parse(value, None)
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError(
                "Cannot parse phone number. Include country code, e.g. +966501234567."
            )
        if not phonenumbers.is_valid_number(parsed):
            raise serializers.ValidationError("Phone number is not valid.")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class SendRegistrationOTPSerializer(serializers.Serializer):
    phone_number = PhoneField()


class CompleteRegistrationSerializer(serializers.Serializer):
    phone_number = PhoneField()
    otp_code = serializers.CharField(min_length=6, max_length=6)
    full_name = serializers.CharField(max_length=255)
    password = serializers.CharField(min_length=8, write_only=True)
    pin = serializers.CharField(min_length=4, max_length=6, write_only=True)

    def validate_otp_code(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be numeric.")
        return value

    def validate_pin(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain digits only.")
        return value


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class SendLoginOTPSerializer(serializers.Serializer):
    phone_number = PhoneField()


class LoginSerializer(serializers.Serializer):
    phone_number = PhoneField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    pin = serializers.CharField(
        min_length=4,
        max_length=6,
        write_only=True,
        required=False,
        allow_blank=True,
    )
    otp_code = serializers.CharField(
        min_length=6,
        max_length=6,
        required=False,
        allow_blank=True,
        write_only=True,
    )

    def validate(self, data: dict) -> dict:
        if not data.get("password") and not data.get("pin"):
            raise serializers.ValidationError(
                "Either 'password' or 'pin' is required."
            )
        return data

    def validate_otp_code(self, value: str) -> str:
        if value and not value.isdigit():
            raise serializers.ValidationError("OTP must be numeric.")
        return value


class FirstLoginSendOTPSerializer(serializers.Serializer):
    phone_number = PhoneField()


class FirstLoginCompleteSerializer(serializers.Serializer):
    phone_number = PhoneField()
    otp_code = serializers.CharField(min_length=6, max_length=6)
    password = serializers.CharField(min_length=8, write_only=True)
    pin = serializers.CharField(min_length=4, max_length=6, write_only=True)

    def validate_otp_code(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be numeric.")
        return value

    def validate_pin(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain digits only.")
        return value


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

class SendPasswordResetOTPSerializer(serializers.Serializer):
    phone_number = PhoneField()


class ConfirmPasswordResetSerializer(serializers.Serializer):
    phone_number = PhoneField()
    otp_code = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate_otp_code(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be numeric.")
        return value


# ---------------------------------------------------------------------------
# PIN reset
# ---------------------------------------------------------------------------

class SendPINResetOTPSerializer(serializers.Serializer):
    phone_number = PhoneField()


class ConfirmPINResetSerializer(serializers.Serializer):
    phone_number = PhoneField()
    otp_code = serializers.CharField(min_length=6, max_length=6)
    new_pin = serializers.CharField(min_length=4, max_length=6, write_only=True)

    def validate_otp_code(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be numeric.")
        return value

    def validate_new_pin(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain digits only.")
        return value
