"""
Security app services — all write operations for OTP, login, device, and lock flows.

Design rules:
  - verify_otp uses SELECT FOR UPDATE to prevent race conditions.
  - OTP plaintext is returned once to the caller; never persisted.
  - lock_user / unlock_user touch User.is_active (Django login gate) and
    create AccountLockEvent records (audit trail).
  - This module does NOT import from accounts, ledger, or payments.
"""
from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction as db_transaction
from django.utils import timezone

from .constants import (
    FAILED_LOGIN_WINDOW_MINUTES,
    MAX_FAILED_LOGIN_ATTEMPTS,
    OTP_EXPIRY_MINUTES,
    LockEventType,
    LoginStatus,
    OTPStatus,
    ResetType,
)
from .exceptions import (
    OTPExpiredError,
    OTPInvalidError,
    OTPMaxAttemptsExceededError,
    OTPNotFoundError,
)
from .models import (
    AccountLockEvent,
    LoginLog,
    OTPRequest,
    PasswordResetAudit,
    UserDevice,
)

logger = logging.getLogger("apps.security")


# ---------------------------------------------------------------------------
# OTP helpers
# ---------------------------------------------------------------------------

def _generate_otp_code() -> str:
    """Cryptographically secure 6-digit numeric OTP."""
    return str(secrets.randbelow(1_000_000)).zfill(6)


# ---------------------------------------------------------------------------
# OTP issuance
# ---------------------------------------------------------------------------

def create_otp(
    *,
    phone: str,
    request_type: str,
    purpose_ref: str = "",
    ip: str | None = None,
    device_id: str = "",
    user=None,
) -> tuple[OTPRequest, str]:
    """
    Issues a fresh OTP for the given phone / request type.

    Any existing PENDING OTP for the same (phone, type, purpose_ref) is
    cancelled before the new one is created — prevents stale codes.

    Returns (OTPRequest, plaintext_otp).
    The plaintext is returned exactly once; never stored.
    """
    OTPRequest.objects.filter(
        phone_number=phone,
        request_type=request_type,
        purpose_reference=purpose_ref,
        status=OTPStatus.PENDING,
    ).update(status=OTPStatus.CANCELLED)

    otp_plain = _generate_otp_code()
    otp_hash = make_password(otp_plain)

    otp = OTPRequest.objects.create(
        user=user,
        phone_number=phone,
        request_type=request_type,
        purpose_reference=purpose_ref,
        otp_hash=otp_hash,
        status=OTPStatus.PENDING,
        expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
        ip_address=ip,
        device_id=device_id,
    )

    logger.debug(
        "OTP issued | type=%s phone=%s id=%s",
        request_type,
        phone,
        otp.pk,
    )
    return otp, otp_plain


# ---------------------------------------------------------------------------
# OTP verification
# ---------------------------------------------------------------------------

def verify_otp(
    *,
    phone: str,
    request_type: str,
    otp_plain: str,
    purpose_ref: str = "",
) -> OTPRequest:
    """
    Verifies an OTP code against the latest PENDING record.

    SELECT FOR UPDATE prevents two concurrent requests from both passing.

    IMPORTANT: all DB writes happen inside the atomic block; exceptions are
    raised *after* the block exits so the saves are always committed.
    Raising inside atomic() would roll back the writes (attempts counter, etc.).

    Raises domain exceptions instead of returning booleans, so callers are
    forced to handle every failure mode explicitly.
    """
    exc_to_raise = None
    verified_otp: OTPRequest | None = None

    with db_transaction.atomic():
        otp = (
            OTPRequest.objects.select_for_update()
            .filter(
                phone_number=phone,
                request_type=request_type,
                purpose_reference=purpose_ref,
                status=OTPStatus.PENDING,
            )
            .order_by("-created_at")
            .first()
        )

        if otp is None:
            exc_to_raise = OTPNotFoundError("No active OTP found.")

        elif timezone.now() > otp.expires_at:
            otp.status = OTPStatus.EXPIRED
            otp.save(update_fields=["status"])
            exc_to_raise = OTPExpiredError("OTP has expired.")

        elif otp.attempts_count >= otp.max_attempts:
            otp.status = OTPStatus.FAILED
            otp.save(update_fields=["status"])
            exc_to_raise = OTPMaxAttemptsExceededError("Maximum OTP attempts exceeded.")

        elif not check_password(otp_plain, otp.otp_hash):
            otp.attempts_count += 1
            if otp.attempts_count >= otp.max_attempts:
                otp.status = OTPStatus.FAILED
            otp.save(update_fields=["attempts_count", "status"])
            exc_to_raise = OTPInvalidError("Invalid OTP code.")

        else:
            otp.status = OTPStatus.VERIFIED
            otp.verified_at = timezone.now()
            otp.save(update_fields=["status", "verified_at"])
            verified_otp = otp

    # Raise outside atomic() so all DB writes above are committed first
    if exc_to_raise is not None:
        raise exc_to_raise

    logger.debug("OTP verified | type=%s phone=%s id=%s", request_type, phone, verified_otp.pk)
    return verified_otp


# ---------------------------------------------------------------------------
# Login logging
# ---------------------------------------------------------------------------

def record_login(
    *,
    phone: str,
    status: str,
    user=None,
    ip: str | None = None,
    device_id: str = "",
    device: str = "",
    user_agent: str = "",
    failure_reason: str = "",
) -> LoginLog:
    log = LoginLog.objects.create(
        user=user,
        phone_number=phone,
        status=status,
        ip_address=ip,
        device_id=device_id,
        device=device,
        user_agent=user_agent,
        failure_reason=failure_reason,
    )
    # Score the login for fraud signals (synchronous; wrapped so it never affects login)
    try:
        from apps.risk.services import score_login
        score_login(log.pk)
    except Exception:
        pass
    return log


# ---------------------------------------------------------------------------
# Device tracking
# ---------------------------------------------------------------------------

def register_or_update_device(
    *,
    user,
    device_uuid: str,
    device_name: str = "",
    platform: str = "",
    os_version: str = "",
    app_version: str = "",
    device_hash: str = "",
    ip: str | None = None,
) -> UserDevice:
    """
    Upserts a device record for the user.
    No biometric data is accepted or stored.
    """
    device, _ = UserDevice.objects.get_or_create(
        device_uuid=device_uuid,
        defaults={
            "user": user,
            "device_name": device_name,
            "platform": platform,
            "os_version": os_version,
            "app_version": app_version,
            "device_hash": device_hash or device_uuid,
            "last_login_ip": ip,
            "last_seen_at": timezone.now(),
        },
    )
    if device.pk:
        UserDevice.objects.filter(pk=device.pk).update(
            last_seen_at=timezone.now(),
            last_login_ip=ip,
            app_version=app_version or device.app_version,
        )
    return device


def trust_device(*, user, device_uuid: str) -> UserDevice:
    device = UserDevice.objects.get(user=user, device_uuid=device_uuid)
    device.is_trusted = True
    device.save(update_fields=["is_trusted"])
    return device


# ---------------------------------------------------------------------------
# Lock / Unlock
# ---------------------------------------------------------------------------

def lock_user(
    *,
    user,
    reason: str,
    trigger_source: str,
    locked_by=None,
) -> AccountLockEvent:
    """
    Locks a user's login access.

    Creates an AccountLockEvent and disables Django's is_active flag.
    Does NOT change user.status — that is reserved for financial blocking.
    """
    event = AccountLockEvent.objects.create(
        user=user,
        event_type=LockEventType.LOCKED,
        reason=reason,
        trigger_source=trigger_source,
        locked_by=locked_by,
        is_active=True,
    )
    # Use .update() to avoid reloading the full model
    user.__class__.objects.filter(pk=user.pk).update(is_active=False)

    logger.warning(
        "User locked | user_id=%s reason=%s source=%s",
        user.pk,
        reason,
        trigger_source,
    )
    return event


def unlock_user(*, user, unlocked_by=None) -> AccountLockEvent | None:
    """
    Deactivates the active lock and re-enables login access.

    Only re-enables is_active if user.status is ACTIVE or PENDING_VERIFICATION
    (blocked users must go through a separate unblock flow).
    """
    from apps.users.constants import UserStatus

    active_lock = AccountLockEvent.objects.filter(
        user=user,
        event_type=LockEventType.LOCKED,
        is_active=True,
    ).first()

    if active_lock:
        active_lock.is_active = False
        active_lock.resolved_at = timezone.now()
        active_lock.unlocked_by = unlocked_by
        active_lock.save(update_fields=["is_active", "resolved_at", "unlocked_by"])

    if user.status in (UserStatus.ACTIVE, UserStatus.PENDING_VERIFICATION):
        user.__class__.objects.filter(pk=user.pk).update(is_active=True)

    logger.info("User unlocked | user_id=%s by=%s", user.pk, getattr(unlocked_by, "pk", None))
    return active_lock


# ---------------------------------------------------------------------------
# Auto-lock on failed logins
# ---------------------------------------------------------------------------

def check_and_auto_lock_user(*, user, phone: str) -> bool:
    """
    Counts failed logins in the configured window.
    If threshold is reached, locks the user and returns True.
    """
    from .selectors import count_failed_logins

    count = count_failed_logins(
        user=user,
        window_minutes=FAILED_LOGIN_WINDOW_MINUTES,
    )
    if count >= MAX_FAILED_LOGIN_ATTEMPTS:
        lock_user(
            user=user,
            reason=f"Auto-locked after {count} failed login attempts.",
            trigger_source="AUTO_LOGIN_FAIL",
        )
        logger.warning(
            "Auto-lock triggered | user_id=%s phone=%s failed_count=%s",
            user.pk,
            phone,
            count,
        )
        return True
    return False


# ---------------------------------------------------------------------------
# Password / PIN reset audit
# ---------------------------------------------------------------------------

def record_password_reset(
    *,
    user,
    reset_type: str,
    initiated_by=None,
    otp_request: OTPRequest | None = None,
    ip: str | None = None,
    success: bool = False,
) -> PasswordResetAudit:
    return PasswordResetAudit.objects.create(
        user=user,
        reset_type=reset_type,
        initiated_by=initiated_by,
        otp_request=otp_request,
        ip_address=ip,
        success=success,
    )
