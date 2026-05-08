"""
Security app models:
  OTPRequest, LoginLog, UserDevice, AccountLockEvent, PasswordResetAudit
"""
from django.conf import settings
from django.db import models

from .constants import (
    LockEventType,
    LoginStatus,
    OTPRequestType,
    OTPStatus,
    ResetType,
)


# ---------------------------------------------------------------------------
# OTPRequest
# ---------------------------------------------------------------------------

class OTPRequest(models.Model):
    """
    Stores every OTP issuance event.
    Only the hashed OTP value is persisted — never plaintext.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="otp_requests",
    )
    phone_number = models.CharField(max_length=20)
    request_type = models.CharField(
        max_length=30,
        choices=OTPRequestType.CHOICES,
    )
    # Allows correlating an OTP to a specific operation (e.g. transaction ID)
    purpose_reference = models.CharField(max_length=100, blank=True)

    # Hashed OTP — never store raw value
    otp_hash = models.CharField(max_length=255)

    status = models.CharField(
        max_length=20,
        choices=OTPStatus.CHOICES,
        default=OTPStatus.PENDING,
    )
    attempts_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)

    sent_via = models.CharField(max_length=20, default="SMS")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_id = models.CharField(max_length=128, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "otp_requests"
        indexes = [
            models.Index(fields=["phone_number", "created_at"]),
            models.Index(fields=["request_type", "status"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["purpose_reference"]),
        ]

    def __str__(self) -> str:
        return f"OTP {self.request_type} for {self.phone_number} [{self.status}]"

    @property
    def is_usable(self) -> bool:
        from django.utils import timezone
        return (
            self.status == OTPStatus.PENDING
            and self.attempts_count < self.max_attempts
            and self.expires_at > timezone.now()
        )


# ---------------------------------------------------------------------------
# LoginLog
# ---------------------------------------------------------------------------

class LoginLog(models.Model):
    """
    Immutable record of every login attempt — success and failure.
    Used for security analytics and fraud scoring.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="login_logs",
    )
    phone_number = models.CharField(max_length=20)
    device = models.CharField(max_length=255, blank=True)
    device_id = models.CharField(max_length=128, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    location_country = models.CharField(max_length=100, blank=True)
    location_city = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=20,
        choices=LoginStatus.CHOICES,
    )
    failure_reason = models.CharField(max_length=100, blank=True)
    risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "login_logs"
        indexes = [
            models.Index(fields=["phone_number", "attempted_at"]),
            models.Index(fields=["user", "attempted_at"]),
            models.Index(fields=["status", "attempted_at"]),
            models.Index(fields=["device_id"]),
        ]

    def __str__(self) -> str:
        return f"Login {self.status} — {self.phone_number} @ {self.attempted_at}"


# ---------------------------------------------------------------------------
# UserDevice
# ---------------------------------------------------------------------------

class UserDevice(models.Model):
    """
    Tracks devices used to access the system.
    No biometric or fingerprint data is stored.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="devices",
    )
    device_uuid = models.CharField(max_length=128, unique=True)
    device_name = models.CharField(max_length=255, blank=True)
    platform = models.CharField(max_length=30, blank=True)
    os_version = models.CharField(max_length=50, blank=True)
    app_version = models.CharField(max_length=50, blank=True)

    # A non-reversible hash of stable device attributes (no biometrics)
    device_hash = models.CharField(max_length=255)

    is_trusted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "user_devices"
        indexes = [
            models.Index(fields=["device_uuid"]),
            models.Index(fields=["user", "is_trusted"]),
            models.Index(fields=["last_seen_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} — {self.device_name} ({self.platform})"


# ---------------------------------------------------------------------------
# AccountLockEvent
# ---------------------------------------------------------------------------

class AccountLockEvent(models.Model):
    """
    Append-only history of user login-access locks and unlocks.
    Separate from account financial restrictions (AccountRestriction in accounts app).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="account_lock_events",
    )
    event_type = models.CharField(
        max_length=20,
        choices=LockEventType.CHOICES,
    )
    reason = models.CharField(max_length=255)
    trigger_source = models.CharField(max_length=30)  # e.g. "AUTO_OTP_FAIL", "STAFF"
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="locked_user_events",
    )
    unlocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="unlocked_user_events",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "account_lock_events"
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["event_type", "occurred_at"]),
        ]

    def __str__(self) -> str:
        return f"Lock {self.event_type} for user {self.user_id} @ {self.occurred_at}"


# ---------------------------------------------------------------------------
# PasswordResetAudit
# ---------------------------------------------------------------------------

class PasswordResetAudit(models.Model):
    """
    Immutable record of every password or PIN reset — self-service or staff-assisted.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="password_reset_audits",
    )
    reset_type = models.CharField(
        max_length=20,
        choices=ResetType.CHOICES,
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="initiated_password_resets",
    )
    otp_request = models.ForeignKey(
        OTPRequest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="password_reset_audits",
    )
    reason = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_reset_audits"
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["initiated_by", "created_at"]),
            models.Index(fields=["reset_type", "success"]),
        ]

    def __str__(self) -> str:
        return f"Reset {self.reset_type} for user {self.user_id} — success={self.success}"
