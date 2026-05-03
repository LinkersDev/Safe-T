from __future__ import annotations

from django.conf import settings

from apps.security.otp.interfaces import OTPIssueResult
from apps.security.services import create_otp, verify_otp


class WhatsAppOTPService:
    """
    Placeholder for Meta WhatsApp Cloud API integration.

    DO NOT implement external calls yet — scaffold only.
    """

    def generate_otp(
        self,
        *,
        phone: str,
        request_type: str,
        purpose_ref: str = "",
        ip: str | None = None,
        device_id: str = "",
        user=None,
    ) -> OTPIssueResult:
        otp, otp_plain = create_otp(
            phone=phone,
            request_type=request_type,
            purpose_ref=purpose_ref,
            ip=ip,
            device_id=device_id,
            user=user,
        )

        # Prepare future payload (template-based messaging)
        _ = {
            "to": phone,
            "template_name": getattr(settings, "WHATSAPP_TEMPLATE_NAME", ""),
            "phone_number_id": getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", ""),
            "access_token": "set via WHATSAPP_ACCESS_TOKEN",
            "variables": {"otp": otp_plain},
        }
        raise NotImplementedError("WhatsApp OTP delivery is not enabled yet.")

    def verify_otp(
        self,
        *,
        phone: str,
        request_type: str,
        otp_plain: str,
        purpose_ref: str = "",
    ):
        return verify_otp(
            phone=phone,
            request_type=request_type,
            otp_plain=otp_plain,
            purpose_ref=purpose_ref,
        )

