"""
Unit tests for security.services.

Run:  python manage.py test apps.security.tests.test_services --settings=config.settings.dev
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.utils import timezone

from apps.users.models import Role, User
from apps.users.constants import RoleCode, UserStatus

from apps.security.constants import (
    OTPRequestType,
    OTPStatus,
    LoginStatus,
    LockEventType,
    MAX_FAILED_LOGIN_ATTEMPTS,
    FAILED_LOGIN_WINDOW_MINUTES,
)
from apps.security.exceptions import (
    OTPExpiredError,
    OTPInvalidError,
    OTPMaxAttemptsExceededError,
    OTPNotFoundError,
)
from apps.security.models import AccountLockEvent, LoginLog, OTPRequest
from apps.security.services import (
    check_and_auto_lock_user,
    create_otp,
    lock_user,
    record_login,
    unlock_user,
    verify_otp,
)


def _make_customer(phone="+966501234567"):
    role, _ = Role.objects.get_or_create(
        code=RoleCode.CUSTOMER,
        defaults={"name": "Customer", "is_staff_role": False, "is_system_role": True},
    )
    user = User(
        phone_number=phone,
        phone_number_normalized=phone,
        full_name="Test User",
        role=role,
        status=UserStatus.ACTIVE,
        is_active=True,
    )
    user.set_password("TestPass123!")
    user.pin_hash = make_password("1234")
    user.save()
    return user


class CreateOTPTests(TestCase):

    def test_returns_otp_request_and_plaintext(self):
        otp_req, otp_plain = create_otp(
            phone="+966501234567",
            request_type=OTPRequestType.REGISTRATION,
        )
        self.assertIsInstance(otp_req, OTPRequest)
        self.assertEqual(len(otp_plain), 6)
        self.assertTrue(otp_plain.isdigit())

    def test_cancels_previous_pending_otp(self):
        create_otp(phone="+966501234567", request_type=OTPRequestType.LOGIN)
        create_otp(phone="+966501234567", request_type=OTPRequestType.LOGIN)
        pending = OTPRequest.objects.filter(
            phone_number="+966501234567",
            request_type=OTPRequestType.LOGIN,
            status=OTPStatus.PENDING,
        )
        self.assertEqual(pending.count(), 1)

    def test_otp_is_hashed_in_db(self):
        _, otp_plain = create_otp(
            phone="+966501234568",
            request_type=OTPRequestType.REGISTRATION,
        )
        otp_req = OTPRequest.objects.latest("created_at")
        # Hash must never equal the plaintext (hasher-agnostic check)
        self.assertNotEqual(otp_req.otp_hash, otp_plain)
        self.assertGreater(len(otp_req.otp_hash), 10)


class VerifyOTPTests(TestCase):

    def setUp(self):
        self.phone = "+966501234569"
        self.otp_req, self.otp_plain = create_otp(
            phone=self.phone,
            request_type=OTPRequestType.REGISTRATION,
        )

    def test_valid_otp_returns_verified_request(self):
        result = verify_otp(
            phone=self.phone,
            request_type=OTPRequestType.REGISTRATION,
            otp_plain=self.otp_plain,
        )
        self.assertEqual(result.status, OTPStatus.VERIFIED)

    def test_invalid_otp_raises_error(self):
        with self.assertRaises(OTPInvalidError):
            verify_otp(
                phone=self.phone,
                request_type=OTPRequestType.REGISTRATION,
                otp_plain="000000",
            )

    def test_expired_otp_raises_error(self):
        self.otp_req.expires_at = timezone.now() - timedelta(seconds=1)
        self.otp_req.save()
        with self.assertRaises(OTPExpiredError):
            verify_otp(
                phone=self.phone,
                request_type=OTPRequestType.REGISTRATION,
                otp_plain=self.otp_plain,
            )

    def test_exceeded_attempts_raises_error(self):
        self.otp_req.attempts_count = self.otp_req.max_attempts
        self.otp_req.save()
        with self.assertRaises(OTPMaxAttemptsExceededError):
            verify_otp(
                phone=self.phone,
                request_type=OTPRequestType.REGISTRATION,
                otp_plain=self.otp_plain,
            )

    def test_no_otp_raises_not_found(self):
        with self.assertRaises(OTPNotFoundError):
            verify_otp(
                phone="+966500000000",
                request_type=OTPRequestType.REGISTRATION,
                otp_plain="123456",
            )

    def test_attempts_incremented_on_failure(self):
        with self.assertRaises(OTPInvalidError):
            verify_otp(
                phone=self.phone,
                request_type=OTPRequestType.REGISTRATION,
                otp_plain="000000",
            )
        self.otp_req.refresh_from_db()
        self.assertEqual(self.otp_req.attempts_count, 1)


class LockUnlockTests(TestCase):

    def setUp(self):
        self.user = _make_customer("+966501234570")

    def test_lock_creates_event_and_disables_is_active(self):
        lock_user(user=self.user, reason="Test lock", trigger_source="TEST")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(
            AccountLockEvent.objects.filter(user=self.user, is_active=True).exists()
        )

    def test_unlock_reactivates_and_resolves_event(self):
        lock_user(user=self.user, reason="Test lock", trigger_source="TEST")
        unlock_user(user=self.user)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertFalse(
            AccountLockEvent.objects.filter(user=self.user, is_active=True).exists()
        )


class AutoLockTests(TestCase):

    def setUp(self):
        self.user = _make_customer("+966501234571")

    def test_auto_lock_triggered_after_n_failures(self):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
            record_login(
                phone=self.user.phone_number,
                user=self.user,
                status=LoginStatus.FAILED,
                failure_reason="wrong_credential",
            )
        locked = check_and_auto_lock_user(user=self.user, phone=self.user.phone_number)
        self.assertTrue(locked)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_auto_lock_not_triggered_below_threshold(self):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 1):
            record_login(
                phone=self.user.phone_number,
                user=self.user,
                status=LoginStatus.FAILED,
                failure_reason="wrong_credential",
            )
        locked = check_and_auto_lock_user(user=self.user, phone=self.user.phone_number)
        self.assertFalse(locked)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
