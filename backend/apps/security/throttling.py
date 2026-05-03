"""
Custom DRF throttle classes for SafeT security endpoints.

Extends AnonRateThrottle to support custom window sizes specified in seconds,
e.g. '3/600s' means 3 requests per 600 seconds (10 minutes).
Standard DRF suffixes (s/m/h/d) are also supported.
"""
from rest_framework.throttling import AnonRateThrottle


class CustomWindowThrottle(AnonRateThrottle):
    """
    Throttle supporting custom second-based windows.

    Rate format examples:
      '3/600s'  — 3 requests per 600 seconds
      '5/300s'  — 5 requests per 300 seconds
      '10/m'    — 10 requests per minute (standard DRF)

    Returns None (unlimited) when the scope has no configured rate so the
    class is safe to decorate views even in test environments where
    DEFAULT_THROTTLE_RATES is empty or the scope is absent.
    """

    def get_rate(self) -> str | None:
        """
        Soft-fail if scope is not in settings instead of raising ImproperlyConfigured.
        A None rate makes allow_request() always return True (unlimited).
        """
        return self.THROTTLE_RATES.get(self.scope)

    def parse_rate(self, rate: str | None):
        if rate is None:
            return None, None

        num_str, period = rate.split("/")
        num_requests = int(num_str)

        std = {"s": 1, "m": 60, "h": 3600, "d": 86400}

        if period in std:
            # Standard single-char suffix: 's', 'm', 'h', 'd'
            duration = std[period]
        elif period[-1] == "s" and period[:-1].isdigit():
            # Custom seconds: e.g. '600s'
            duration = int(period[:-1])
        elif period.isdigit():
            # Plain integer seconds: e.g. '600'
            duration = int(period)
        else:
            # Fallback: use last char as standard suffix
            duration = std.get(period[-1], 60)

        return num_requests, duration


class OTPSendThrottle(CustomWindowThrottle):
    """3 OTP send attempts per 10 minutes per IP."""
    scope = "otp_send"


class LoginThrottle(CustomWindowThrottle):
    """5 login attempts per 5 minutes per IP."""
    scope = "login"


class TransferThrottle(CustomWindowThrottle):
    """10 transfer attempts per minute per user. Applied in Phase 5."""
    scope = "transfer"


class QRPayThrottle(CustomWindowThrottle):
    """10 QR payment attempts per minute per user. Applied in Phase 5."""
    scope = "qr_pay"
