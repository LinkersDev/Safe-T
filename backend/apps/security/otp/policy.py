from __future__ import annotations

from django.conf import settings

from apps.security.constants import OTPRequestType


DEV_EXPOSE_ALLOWED_TYPES: set[str] = {
    OTPRequestType.FIRST_LOGIN,
    OTPRequestType.LOGIN,
    OTPRequestType.PASSWORD_RESET,
    OTPRequestType.PIN_RESET,
    # Transaction OTPs (dev only)
    OTPRequestType.TRANSFER,
    OTPRequestType.QR_PAYMENT,
    OTPRequestType.BILL_PAYMENT,
}


def is_dev_otp_enabled() -> bool:
    return bool(settings.DEBUG or getattr(settings, "ENABLE_DEV_OTP", False))


def should_expose_dev_otp(request_type: str) -> bool:
    """
    Only expose plaintext OTP internally during development *and* only for
    sensitive flows explicitly allowed by policy.
    """
    return is_dev_otp_enabled() and request_type in DEV_EXPOSE_ALLOWED_TYPES

