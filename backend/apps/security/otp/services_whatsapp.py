from __future__ import annotations

import logging

from django.conf import settings

from apps.security.otp.clients.tneenwh_client import TneenwhClient, TneenwhError
from apps.security.otp.interfaces import OTPIssueResult
from apps.security.otp.policy import should_expose_dev_otp
from apps.security.services import create_otp, verify_otp

logger = logging.getLogger(__name__)


class WhatsAppOTPService:
    """
    Production OTP service that delivers codes via TNEENWH WhatsApp API.

    * Delegates OTP generation/hashing/storage to ``create_otp()`` — never
      replaces or bypasses the core security logic.
    * Sends the plaintext OTP via the TNEENWH REST API synchronously.
    * In dev mode (DEBUG + ENABLE_DEV_OTP) the OTP is still printed to the
      terminal so developers can test without a live WhatsApp account.
    * OTP verification is delegated unchanged to ``verify_otp()``.
    """

    def __init__(self, client: TneenwhClient | None = None):
        self._client = client or TneenwhClient()

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
        # 1. Generate and persist OTP (core logic — never bypassed)
        otp, otp_plain = create_otp(
            phone=phone,
            request_type=request_type,
            purpose_ref=purpose_ref,
            ip=ip,
            device_id=device_id,
            user=user,
        )

        # 2. Dev-only terminal exposure (unchanged behavior)
        if settings.DEBUG and should_expose_dev_otp(request_type):
            print(f"[WHATSAPP DEV] OTP for {phone}: {otp_plain}")

        # 3. Deliver via WhatsApp
        message = (
            f"Welcome to SaFe-T!\n\n"
            f"Your OTP code is: {otp_plain}\n\n"
            f"Thank you for using SaFe-T."
        )
        try:
            result = self._client.send_message(to=phone, message=message)
            logger.info(
                "WhatsApp OTP sent | phone=%s request_type=%s otp_request_id=%s",
                phone,
                request_type,
                otp.pk,
            )
            if settings.DEBUG:
                print(f"[WHATSAPP DEBUG] API response: {result}")
        except TneenwhError as exc:
            # Log failure but do NOT raise — the OTP is already created and
            # valid; delivery failure should not break the request flow.
            logger.error(
                "WhatsApp OTP delivery failed | phone=%s request_type=%s otp_request_id=%s error=%s",
                phone,
                request_type,
                otp.pk,
                exc,
                exc_info=True,
            )
            # Dev-only: Print error to terminal for immediate visibility
            if settings.DEBUG:
                print(f"[WHATSAPP ERROR] Failed to send OTP to {phone}")
                print(f"[WHATSAPP ERROR] Error type: {type(exc).__name__}")
                print(f"[WHATSAPP ERROR] Error message: {exc}")
                print(f"[WHATSAPP ERROR] OTP request ID: {otp.pk}")

        # 4. Return result — plaintext is None in production
        return OTPIssueResult(
            otp_request_id=otp.pk,
            otp_plain=otp_plain if (settings.DEBUG and should_expose_dev_otp(request_type)) else None,
        )

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

