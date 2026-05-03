from __future__ import annotations

from apps.security.otp.interfaces import OTPIssueResult
from apps.security.otp.policy import should_expose_dev_otp
from apps.security.services import create_otp, verify_otp


class DevOTPService:
    """
    Development-only OTP service.

    - Generates OTP via the existing security.services core.
    - Does not send externally.
    - Returns plaintext OTP only when policy allows.
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
        return OTPIssueResult(
            otp_request_id=otp.pk,
            otp_plain=otp_plain if should_expose_dev_otp(request_type) else None,
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

