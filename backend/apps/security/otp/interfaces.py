from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OTPIssueResult:
    """
    Plaintext OTP is returned to the caller once.
    In production delivery services will send it externally and return None.
    """

    otp_request_id: int
    otp_plain: str | None


class OTPService(Protocol):
    def generate_otp(
        self,
        *,
        phone: str,
        request_type: str,
        purpose_ref: str = "",
        ip: str | None = None,
        device_id: str = "",
        user=None,
    ) -> OTPIssueResult: ...

    def verify_otp(
        self,
        *,
        phone: str,
        request_type: str,
        otp_plain: str,
        purpose_ref: str = "",
    ):
        """Returns OTPRequest on success; raises domain exceptions on failure."""
        ...

