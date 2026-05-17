"""
OTP service that delivers codes via the local wa-otp-mini WhatsApp bot.

The wa-otp-mini process must be running (e.g. via pm2) before this provider
is used. Set OTP_PROVIDER=wa_otp_mini in your .env to activate it.
"""
from __future__ import annotations

import logging

from django.conf import settings

from apps.security.otp.clients.wa_otp_mini_client import WaOtpMiniClient, WaOtpMiniError
from apps.security.otp.interfaces import OTPIssueResult
from apps.security.otp.policy import should_expose_dev_otp
from apps.security.services import create_otp, verify_otp

logger = logging.getLogger(__name__)


class WaOtpMiniService:
    """
    Production OTP service that delivers codes via the local wa-otp-mini bot.

    * OTP generation/hashing/storage is always delegated to create_otp().
    * The plaintext OTP is sent as a WhatsApp message via wa-otp-mini.
    * Delivery failures are logged but do NOT break the request — the OTP
      record is already created and valid.
    * In dev mode (DEBUG + ENABLE_DEV_OTP) the OTP is printed to terminal.
    """

    def __init__(self, client: WaOtpMiniClient | None = None):
        self._client = client or WaOtpMiniClient()

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
        # 1. Generate and persist OTP
        otp, otp_plain = create_otp(
            phone=phone,
            request_type=request_type,
            purpose_ref=purpose_ref,
            ip=ip,
            device_id=device_id,
            user=user,
        )

        # 2. Dev-only terminal exposure
        if settings.DEBUG and should_expose_dev_otp(request_type):
            print(f"[WA-OTP-MINI DEV] OTP for {phone}: {otp_plain}")

        # 3. Deliver via wa-otp-mini
        message = (
            f"*SaFe-T Verification*\n\n"
            f"Your OTP code is: *{otp_plain}*\n\n"
            f"This code expires in 5 minutes.\n"
            f"Do not share it with anyone."
        )
        try:
            self._client.send_message(phone=phone, message=message)
            logger.info(
                "WA-OTP-Mini sent | phone=%s type=%s otp_id=%s",
                phone, request_type, otp.pk,
            )
        except WaOtpMiniError as exc:
            logger.error(
                "WA-OTP-Mini delivery failed | phone=%s type=%s otp_id=%s error=%s",
                phone, request_type, otp.pk, exc,
                exc_info=True,
            )
            if settings.DEBUG:
                print(f"[WA-OTP-MINI ERROR] Failed to send to {phone}: {exc}")

        # 4. Return — plaintext only in dev mode
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
