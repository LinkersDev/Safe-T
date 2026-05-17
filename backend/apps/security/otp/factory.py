from __future__ import annotations

from django.conf import settings

from apps.security.otp.services_dev import DevOTPService
from apps.security.otp.services_wa_otp_mini import WaOtpMiniService
from apps.security.otp.services_whatsapp import WhatsAppOTPService
from apps.security.otp.services_twilio_verify import TwilioVerifyOTPService


def get_otp_service():
    provider = getattr(settings, "OTP_PROVIDER", "dev")
    if provider == "whatsapp":
        return WhatsAppOTPService()
    if provider == "twilio_verify":
        return TwilioVerifyOTPService()
    if provider == "wa_otp_mini":
        return WaOtpMiniService()
    return DevOTPService()

