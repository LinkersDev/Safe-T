"""
Security app selectors — read-only queries.
"""
from __future__ import annotations

from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from .constants import LockEventType, LoginStatus, OTPStatus
from .models import AccountLockEvent, LoginLog, OTPRequest


def get_active_otp(
    *,
    phone: str,
    request_type: str,
    purpose_ref: str = "",
) -> OTPRequest | None:
    """Returns the most recent PENDING OTP for the given (phone, type, purpose)."""
    return (
        OTPRequest.objects.filter(
            phone_number=phone,
            request_type=request_type,
            purpose_reference=purpose_ref,
            status=OTPStatus.PENDING,
        )
        .order_by("-created_at")
        .first()
    )


def count_failed_logins(*, user, window_minutes: int) -> int:
    """Count failed login attempts for a user within the given rolling window."""
    since = timezone.now() - timedelta(minutes=window_minutes)
    return LoginLog.objects.filter(
        user=user,
        status=LoginStatus.FAILED,
        attempted_at__gte=since,
    ).count()


def is_user_locked(*, user) -> bool:
    """True if the user has an active lock event (login-access locked)."""
    return AccountLockEvent.objects.filter(
        user=user,
        event_type=LockEventType.LOCKED,
        is_active=True,
    ).exists()


def get_login_history(*, user, limit: int = 20) -> QuerySet[LoginLog]:
    return (
        LoginLog.objects.filter(user=user)
        .order_by("-attempted_at")
        .select_related("user")[:limit]
    )


def get_active_lock(*, user) -> AccountLockEvent | None:
    return AccountLockEvent.objects.filter(
        user=user,
        event_type=LockEventType.LOCKED,
        is_active=True,
    ).first()
