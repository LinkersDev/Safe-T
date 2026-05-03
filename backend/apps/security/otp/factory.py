from __future__ import annotations

from django.conf import settings

from apps.security.otp.services_dev import DevOTPService
from apps.security.otp.services_whatsapp import WhatsAppOTPService


def get_otp_service():
    provider = getattr(settings, "OTP_PROVIDER", "dev")
    if provider == "whatsapp":
        return WhatsAppOTPService()
    return DevOTPService()

