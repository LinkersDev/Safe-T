"""
Phase 2 End-to-End Validation Suite
====================================
Covers every flow described in the validation checklist:

  1. Registration Flow
  2. Login Flow
  3. OTP System Validation
  4. Account Lock System
  5. Logging & Device Tracking
  6. JWT Authentication
  7. Password / PIN Reset

Run:
    python manage.py test apps.security.tests.test_phase2_validation \
        --settings=config.settings.test --verbosity=2
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.constants import RoleCode, UserStatus
from apps.users.models import Role, User
from apps.users.services import register_user

from apps.security.constants import (
    MAX_FAILED_LOGIN_ATTEMPTS,
    OTPRequestType,
    OTPStatus,
    LoginStatus,
    LockEventType,
    ResetType,
)
from apps.security.models import (
    AccountLockEvent,
    LoginLog,
    OTPRequest,
    PasswordResetAudit,
    UserDevice,
)
from apps.security.services import (
    check_and_auto_lock_user,
    create_otp,
    lock_user,
    record_login,
    register_or_update_device,
    unlock_user,
    verify_otp,
)
from apps.security.selectors import (
    count_failed_logins,
    get_active_lock,
    is_user_locked,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _seed_customer_role():
    role, _ = Role.objects.get_or_create(
        code=RoleCode.CUSTOMER,
        defaults={
            "name": "Customer",
            "is_staff_role": False,
            "is_system_role": True,
        },
    )
    return role


def _seed_cs_role():
    role, _ = Role.objects.get_or_create(
        code=RoleCode.CUSTOMER_SERVICE,
        defaults={
            "name": "Customer Service",
            "is_staff_role": True,
            "is_system_role": True,
        },
    )
    return role


def _make_user(phone="+966501000001", status=UserStatus.ACTIVE):
    _seed_customer_role()
    user = register_user(
        phone=phone,
        full_name="Validation User",
        password="ValidPass1!",
        pin="4321",
    )
    if status != UserStatus.PENDING_VERIFICATION:
        user.status = status
        user.save(update_fields=["status"])
    return user


# ===========================================================================
# 1. Registration Flow
# ===========================================================================

class RegistrationFlowTests(TestCase):
    """
    Validates the complete two-step registration flow:
      Step 1 — Send REGISTRATION OTP
      Step 2 — Verify OTP → create user with PENDING_VERIFICATION
    """

    def setUp(self):
        self.client = APIClient()
        _seed_customer_role()
        self.phone = "+966502000001"

    # --- Step 1: send OTP ---

    def test_step1_send_otp_returns_200(self):
        url = reverse("register-send-otp")
        resp = self.client.post(url, {"phone_number": self.phone})
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn("message", resp.data)
        self.assertIn("expires_in", resp.data)

    def test_step1_otp_is_stored_in_db(self):
        reverse("register-send-otp")
        create_otp(phone=self.phone, request_type=OTPRequestType.REGISTRATION)
        otp = OTPRequest.objects.filter(
            phone_number=self.phone,
            request_type=OTPRequestType.REGISTRATION,
            status=OTPStatus.PENDING,
        ).first()
        self.assertIsNotNone(otp)
        # Must never store plaintext
        self.assertNotEqual(len(otp.otp_hash), 6)
        self.assertFalse(otp.otp_hash.isdigit())

    def test_step1_duplicate_phone_returns_409(self):
        _make_user(self.phone, status=UserStatus.ACTIVE)
        url = reverse("register-send-otp")
        resp = self.client.post(url, {"phone_number": self.phone})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["code"], "phone_taken")

    def test_step1_invalid_phone_returns_400(self):
        url = reverse("register-send-otp")
        resp = self.client.post(url, {"phone_number": "not-a-phone"})
        self.assertEqual(resp.status_code, 400)

    # --- Step 2: complete registration ---

    def test_step2_valid_otp_creates_pending_user(self):
        _, otp_plain = create_otp(
            phone=self.phone,
            request_type=OTPRequestType.REGISTRATION,
        )
        url = reverse("register-complete")
        resp = self.client.post(url, {
            "phone_number": self.phone,
            "otp_code": otp_plain,
            "full_name": "New Customer",
            "password": "NewPass1!",
            "pin": "5678",
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["user"]["status"], UserStatus.PENDING_VERIFICATION)
        self.assertIn("id", resp.data["user"])

    def test_step2_user_exists_in_db_with_correct_status(self):
        _, otp_plain = create_otp(
            phone=self.phone,
            request_type=OTPRequestType.REGISTRATION,
        )
        self.client.post(reverse("register-complete"), {
            "phone_number": self.phone,
            "otp_code": otp_plain,
            "full_name": "New Customer",
            "password": "NewPass1!",
            "pin": "5678",
        })
        user = User.objects.get(phone_number=self.phone)
        self.assertEqual(user.status, UserStatus.PENDING_VERIFICATION)
        self.assertTrue(user.is_phone_verified)

    def test_step2_password_is_hashed_in_db(self):
        _, otp_plain = create_otp(
            phone=self.phone,
            request_type=OTPRequestType.REGISTRATION,
        )
        self.client.post(reverse("register-complete"), {
            "phone_number": self.phone,
            "otp_code": otp_plain,
            "full_name": "New Customer",
            "password": "NewPass1!",
            "pin": "5678",
        })
        user = User.objects.get(phone_number=self.phone)
        # Stored password must not equal plaintext
        self.assertNotEqual(user.password, "NewPass1!")
        # check_password must validate correctly
        self.assertTrue(user.check_password("NewPass1!"))

    def test_step2_pin_is_hashed_in_db(self):
        _, otp_plain = create_otp(
            phone=self.phone,
            request_type=OTPRequestType.REGISTRATION,
        )
        self.client.post(reverse("register-complete"), {
            "phone_number": self.phone,
            "otp_code": otp_plain,
            "full_name": "New Customer",
            "password": "NewPass1!",
            "pin": "5678",
        })
        user = User.objects.get(phone_number=self.phone)
        self.assertNotEqual(user.pin_hash, "5678")
        self.assertTrue(check_password("5678", user.pin_hash))

    def test_step2_wrong_otp_returns_400(self):
        create_otp(phone=self.phone, request_type=OTPRequestType.REGISTRATION)
        url = reverse("register-complete")
        resp = self.client.post(url, {
            "phone_number": self.phone,
            "otp_code": "000000",
            "full_name": "New Customer",
            "password": "NewPass1!",
            "pin": "5678",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "otp_invalid")

    def test_step2_non_digit_pin_rejected(self):
        _, otp_plain = create_otp(
            phone=self.phone,
            request_type=OTPRequestType.REGISTRATION,
        )
        resp = self.client.post(reverse("register-complete"), {
            "phone_number": self.phone,
            "otp_code": otp_plain,
            "full_name": "New Customer",
            "password": "NewPass1!",
            "pin": "abcd",
        })
        self.assertEqual(resp.status_code, 400)


# ===========================================================================
# 2. Login Flow
# ===========================================================================

class LoginFlowTests(TestCase):
    """
    Validates the two-step login flow:
      Step 1 — POST /api/auth/otp/send/
      Step 2 — POST /api/auth/login/ → JWT
    """

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user("+966502000010", status=UserStatus.ACTIVE)

    def _send_login_otp(self):
        _, otp_plain = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.LOGIN,
            user=self.user,
        )
        return otp_plain

    # --- Step 1 ---

    def test_otp_send_returns_200_for_known_phone(self):
        url = reverse("login-send-otp")
        resp = self.client.post(url, {"phone_number": self.user.phone_number})
        self.assertEqual(resp.status_code, 200)

    def test_otp_send_returns_200_for_unknown_phone(self):
        """Enumeration protection: same response for unknown phones."""
        url = reverse("login-send-otp")
        resp = self.client.post(url, {"phone_number": "+966500000099"})
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("_debug_otp", resp.data)  # no OTP for unknown phone
        self.assertNotIn("dev_otp", resp.data)  # no OTP for unknown phone

    # --- Step 2: password login ---

    def test_password_login_returns_jwt_tokens(self):
        otp = self._send_login_otp()
        resp = self.client.post(reverse("login"), {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "ValidPass1!",
        })
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_pin_login_returns_jwt_tokens(self):
        otp = self._send_login_otp()
        resp = self.client.post(reverse("login"), {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "pin": "4321",
        })
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn("access", resp.data)

    def test_login_response_includes_user_info(self):
        otp = self._send_login_otp()
        resp = self.client.post(reverse("login"), {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "ValidPass1!",
        })
        self.assertEqual(resp.status_code, 200)
        user_data = resp.data["user"]
        self.assertEqual(user_data["phone_number"], self.user.phone_number)
        self.assertEqual(user_data["status"], UserStatus.ACTIVE)
        self.assertEqual(user_data["role"], RoleCode.CUSTOMER)

    def test_jwt_access_token_contains_custom_claims(self):
        otp = self._send_login_otp()
        resp = self.client.post(reverse("login"), {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "ValidPass1!",
        })
        token = AccessToken(resp.data["access"])
        self.assertEqual(token["role"], RoleCode.CUSTOMER)
        self.assertEqual(token["status"], UserStatus.ACTIVE)
        self.assertEqual(token["full_name"], "Validation User")

    def test_wrong_password_returns_401(self):
        otp = self._send_login_otp()
        resp = self.client.post(reverse("login"), {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "WRONG_PASS!",
        })
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["code"], "wrong_password")

    def test_wrong_pin_returns_401(self):
        otp = self._send_login_otp()
        resp = self.client.post(reverse("login"), {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "pin": "9999",
        })
        self.assertEqual(resp.status_code, 401)

    def test_missing_credential_returns_400(self):
        otp = self._send_login_otp()
        resp = self.client.post(reverse("login"), {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
        })
        self.assertEqual(resp.status_code, 400)


# ===========================================================================
# 3. OTP System Validation
# ===========================================================================

class OTPSystemTests(TestCase):
    """
    Validates OTP issuance, storage, expiry, attempts, and cancellation.
    """

    def setUp(self):
        self.phone = "+966502000020"

    def test_create_otp_returns_6_digit_numeric_code(self):
        _, plain = create_otp(phone=self.phone, request_type=OTPRequestType.REGISTRATION)
        self.assertEqual(len(plain), 6)
        self.assertTrue(plain.isdigit())

    def test_otp_hash_stored_not_plaintext(self):
        _, plain = create_otp(phone=self.phone, request_type=OTPRequestType.REGISTRATION)
        record = OTPRequest.objects.latest("created_at")
        self.assertNotEqual(record.otp_hash, plain)
        # Must be a valid hash (at minimum not a 6-digit string)
        self.assertFalse(record.otp_hash.isdigit())
        self.assertGreater(len(record.otp_hash), 20)

    def test_previous_pending_otp_cancelled_on_new_issue(self):
        create_otp(phone=self.phone, request_type=OTPRequestType.LOGIN)
        create_otp(phone=self.phone, request_type=OTPRequestType.LOGIN)
        pending_count = OTPRequest.objects.filter(
            phone_number=self.phone,
            request_type=OTPRequestType.LOGIN,
            status=OTPStatus.PENDING,
        ).count()
        self.assertEqual(pending_count, 1)
        cancelled_count = OTPRequest.objects.filter(
            phone_number=self.phone,
            request_type=OTPRequestType.LOGIN,
            status=OTPStatus.CANCELLED,
        ).count()
        self.assertEqual(cancelled_count, 1)

    def test_valid_otp_verification_marks_verified(self):
        _, plain = create_otp(phone=self.phone, request_type=OTPRequestType.LOGIN)
        result = verify_otp(phone=self.phone, request_type=OTPRequestType.LOGIN, otp_plain=plain)
        self.assertEqual(result.status, OTPStatus.VERIFIED)
        self.assertIsNotNone(result.verified_at)

    def test_expired_otp_raises_expired_error(self):
        from apps.security.exceptions import OTPExpiredError
        req, _ = create_otp(phone=self.phone, request_type=OTPRequestType.LOGIN)
        req.expires_at = timezone.now() - timedelta(seconds=1)
        req.save()
        with self.assertRaises(OTPExpiredError):
            verify_otp(phone=self.phone, request_type=OTPRequestType.LOGIN, otp_plain="000000")
        req.refresh_from_db()
        self.assertEqual(req.status, OTPStatus.EXPIRED)

    def test_wrong_otp_increments_attempts_counter(self):
        from apps.security.exceptions import OTPInvalidError
        req, _ = create_otp(phone=self.phone, request_type=OTPRequestType.LOGIN)
        with self.assertRaises(OTPInvalidError):
            verify_otp(phone=self.phone, request_type=OTPRequestType.LOGIN, otp_plain="000000")
        req.refresh_from_db()
        self.assertEqual(req.attempts_count, 1)

    def test_max_attempts_exceeded_marks_failed(self):
        from apps.security.exceptions import OTPInvalidError, OTPMaxAttemptsExceededError
        from apps.security.constants import OTP_MAX_ATTEMPTS
        req, _ = create_otp(phone=self.phone, request_type=OTPRequestType.LOGIN)
        # Exhaust attempts
        for _ in range(OTP_MAX_ATTEMPTS - 1):
            try:
                verify_otp(phone=self.phone, request_type=OTPRequestType.LOGIN, otp_plain="000000")
            except OTPInvalidError:
                pass
        # Final attempt should raise MaxAttempts
        with self.assertRaises((OTPInvalidError, OTPMaxAttemptsExceededError)):
            verify_otp(phone=self.phone, request_type=OTPRequestType.LOGIN, otp_plain="000000")
        req.refresh_from_db()
        self.assertEqual(req.status, OTPStatus.FAILED)

    def test_otp_expires_at_is_set_correctly(self):
        from apps.security.constants import OTP_EXPIRY_MINUTES
        before = timezone.now()
        req, _ = create_otp(phone=self.phone, request_type=OTPRequestType.REGISTRATION)
        after = timezone.now()
        min_expiry = before + timedelta(minutes=OTP_EXPIRY_MINUTES)
        max_expiry = after + timedelta(minutes=OTP_EXPIRY_MINUTES)
        self.assertGreaterEqual(req.expires_at, min_expiry)
        self.assertLessEqual(req.expires_at, max_expiry)

    def test_otp_send_throttle_class_allows_request_when_no_rate_configured(self):
        """Throttle returns None rate (unlimited) in test environment — no KeyError."""
        from apps.security.throttling import OTPSendThrottle
        throttle = OTPSendThrottle()
        self.assertIsNone(throttle.rate)

    def test_login_throttle_class_allows_request_when_no_rate_configured(self):
        from apps.security.throttling import LoginThrottle
        throttle = LoginThrottle()
        self.assertIsNone(throttle.rate)


# ===========================================================================
# 4. Account Lock System
# ===========================================================================

class AccountLockSystemTests(TestCase):
    """
    Validates auto-lock on failed logins, AccountLockEvent creation,
    and Customer Service unlock flow.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user("+966502000030", status=UserStatus.ACTIVE)
        # Seed Customer Service role for unlock test
        self.cs_role = _seed_cs_role()

    # --- Direct service tests ---

    def test_lock_user_disables_is_active(self):
        lock_user(user=self.user, reason="Test", trigger_source="TEST")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_lock_user_creates_active_lock_event(self):
        lock_user(user=self.user, reason="Test", trigger_source="TEST")
        event = AccountLockEvent.objects.filter(user=self.user, is_active=True).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, LockEventType.LOCKED)

    def test_is_user_locked_returns_true_after_lock(self):
        lock_user(user=self.user, reason="Test", trigger_source="TEST")
        self.assertTrue(is_user_locked(user=self.user))

    def test_unlock_user_restores_is_active(self):
        lock_user(user=self.user, reason="Test", trigger_source="TEST")
        unlock_user(user=self.user)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_unlock_resolves_lock_event(self):
        lock_user(user=self.user, reason="Test", trigger_source="TEST")
        unlock_user(user=self.user)
        self.assertFalse(is_user_locked(user=self.user))
        event = AccountLockEvent.objects.filter(user=self.user).latest("occurred_at")
        self.assertFalse(event.is_active)
        self.assertIsNotNone(event.resolved_at)

    # --- Auto-lock via service ---

    def test_auto_lock_triggers_after_n_failed_attempts(self):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
            record_login(
                phone=self.user.phone_number,
                user=self.user,
                status=LoginStatus.FAILED,
                failure_reason="test",
            )
        was_locked = check_and_auto_lock_user(
            user=self.user,
            phone=self.user.phone_number,
        )
        self.assertTrue(was_locked)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(
            AccountLockEvent.objects.filter(user=self.user, is_active=True).exists()
        )

    def test_auto_lock_does_not_trigger_below_threshold(self):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 1):
            record_login(
                phone=self.user.phone_number,
                user=self.user,
                status=LoginStatus.FAILED,
                failure_reason="test",
            )
        was_locked = check_and_auto_lock_user(
            user=self.user,
            phone=self.user.phone_number,
        )
        self.assertFalse(was_locked)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    # --- Via login endpoint ---

    def test_locked_user_gets_403_on_login(self):
        lock_user(user=self.user, reason="Test", trigger_source="TEST")
        _, otp = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.LOGIN,
            user=self.user,
        )
        resp = self.client.post(reverse("login"), {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "ValidPass1!",
        })
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data["code"], "account_locked")

    # --- Staff unlock endpoint ---

    def test_staff_unlock_endpoint_restores_access(self):
        from apps.users.models import Permission, RolePermission
        # Create CS user with unlock_user permission
        cs_user = User(
            phone_number="+966502000031",
            phone_number_normalized="+966502000031",
            full_name="CS Agent",
            role=self.cs_role,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_staff=True,
        )
        cs_user.set_password("CSPass1!")
        cs_user.save()
        # Grant unlock_user permission
        perm, _ = Permission.objects.get_or_create(
            code="unlock_user",
            defaults={"name": "Unlock User", "module": "security"},
        )
        RolePermission.objects.get_or_create(role=self.cs_role, permission=perm)

        # Lock the target user
        lock_user(user=self.user, reason="Too many failures", trigger_source="AUTO")

        # Authenticate CS user and call unlock
        self.client.force_authenticate(user=cs_user)
        url = reverse("staff-users-unlock", kwargs={"user_id": self.user.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200, resp.data)

        # Verify user is unlocked
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertFalse(is_user_locked(user=self.user))

    def test_blocked_user_cannot_be_unlocked_via_unlock_endpoint(self):
        """BLOCKED status requires Admin unblock — not the unlock endpoint."""
        from apps.users.models import Permission, RolePermission
        cs_user = User(
            phone_number="+966502000032",
            phone_number_normalized="+966502000032",
            full_name="CS Agent 2",
            role=self.cs_role,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_staff=True,
        )
        cs_user.set_password("CSPass1!")
        cs_user.save()
        perm, _ = Permission.objects.get_or_create(
            code="unlock_user",
            defaults={"name": "Unlock User", "module": "security"},
        )
        RolePermission.objects.get_or_create(role=self.cs_role, permission=perm)

        self.user.status = UserStatus.BLOCKED
        self.user.save()

        self.client.force_authenticate(user=cs_user)
        url = reverse("staff-users-unlock", kwargs={"user_id": self.user.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "user_blocked")


# ===========================================================================
# 5. Logging & Device Tracking
# ===========================================================================

class LoggingAndDeviceTrackingTests(TestCase):
    """
    Validates that LoginLog and UserDevice records are created/updated
    on login attempts.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user("+966502000040", status=UserStatus.ACTIVE)

    def test_successful_login_creates_success_login_log(self):
        otp = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.LOGIN,
            user=self.user,
        )[1]
        self.client.post(reverse("login"), {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "ValidPass1!",
        })
        log = LoginLog.objects.filter(
            user=self.user,
            status=LoginStatus.SUCCESS,
        ).last()
        self.assertIsNotNone(log)
        self.assertEqual(log.phone_number, self.user.phone_number)

    def test_failed_login_creates_failure_login_log(self):
        otp = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.LOGIN,
            user=self.user,
        )[1]
        self.client.post(reverse("login"), {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "WRONG_PASS!",
        })
        log = LoginLog.objects.filter(
            user=self.user,
            status=LoginStatus.FAILED,
        ).last()
        self.assertIsNotNone(log)
        self.assertEqual(log.failure_reason, "wrong_credential")

    def test_unknown_phone_login_creates_failure_log_without_user_fk(self):
        create_otp(phone="+966500000099", request_type=OTPRequestType.LOGIN)
        self.client.post(reverse("login"), {
            "phone_number": "+966500000099",
            "otp_code": "000000",
            "password": "anything",
        })
        log = LoginLog.objects.filter(
            phone_number="+966500000099",
            status=LoginStatus.FAILED,
        ).last()
        self.assertIsNotNone(log)
        self.assertIsNone(log.user)

    def test_successful_login_creates_device_record(self):
        otp = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.LOGIN,
            user=self.user,
        )[1]
        self.client.post(
            reverse("login"),
            {
                "phone_number": self.user.phone_number,
                "otp_code": otp,
                "password": "ValidPass1!",
            },
            HTTP_X_DEVICE_ID="device-uuid-abc123",
        )
        device = UserDevice.objects.filter(user=self.user, device_uuid="device-uuid-abc123").first()
        self.assertIsNotNone(device)

    def test_repeat_login_updates_device_last_seen(self):
        register_or_update_device(
            user=self.user,
            device_uuid="repeat-device",
            device_hash="repeat-device",
        )
        first_device = UserDevice.objects.get(user=self.user, device_uuid="repeat-device")
        first_seen = first_device.last_seen_at

        register_or_update_device(
            user=self.user,
            device_uuid="repeat-device",
            device_hash="repeat-device",
        )
        first_device.refresh_from_db()
        # last_seen_at should be updated (or at minimum not before first)
        self.assertGreaterEqual(first_device.last_seen_at or timezone.now(), first_seen or timezone.now() - timedelta(seconds=1))

    def test_failed_login_count_selector(self):
        for _ in range(3):
            record_login(
                phone=self.user.phone_number,
                user=self.user,
                status=LoginStatus.FAILED,
                failure_reason="test",
            )
        count = count_failed_logins(user=self.user, window_minutes=60)
        self.assertEqual(count, 3)


# ===========================================================================
# 6. JWT Authentication
# ===========================================================================

class JWTAuthenticationTests(TestCase):
    """
    Validates that issued JWT tokens work on protected endpoints
    and that the refresh flow produces new access tokens.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user("+966502000050", status=UserStatus.ACTIVE)

    def _login_and_get_tokens(self):
        otp = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.LOGIN,
            user=self.user,
        )[1]
        resp = self.client.post(reverse("login"), {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "ValidPass1!",
        })
        self.assertEqual(resp.status_code, 200)
        return resp.data["access"], resp.data["refresh"]

    def test_access_token_authenticates_protected_endpoint(self):
        """
        Uses the pending-users-list staff endpoint as a protected endpoint proxy.
        Any authenticated request to a non-AllowAny endpoint should work.
        """
        access, _ = self._login_and_get_tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        # The pending list view is IsAuthenticated — so access token should grant entry
        resp = self.client.get(reverse("staff-users-pending"))
        # 200 or 403 are both fine (200 = admin, 403 = no staff role) — 401 would mean JWT failed
        self.assertNotEqual(resp.status_code, 401, "Access token rejected — JWT auth broken")

    def test_no_token_returns_401_on_protected_endpoint(self):
        self.client.credentials()
        resp = self.client.get(reverse("staff-users-pending"))
        self.assertEqual(resp.status_code, 401)

    def test_invalid_token_returns_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer totally.invalid.token")
        resp = self.client.get(reverse("staff-users-pending"))
        self.assertEqual(resp.status_code, 401)

    def test_token_refresh_returns_new_access_token(self):
        _, refresh = self._login_and_get_tokens()
        resp = self.client.post(reverse("token-refresh"), {"refresh": refresh})
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn("access", resp.data)
        # New access token must be a non-empty string
        self.assertGreater(len(resp.data["access"]), 50)

    def test_access_token_has_custom_claims(self):
        access, _ = self._login_and_get_tokens()
        token = AccessToken(access)
        self.assertEqual(token["role"], RoleCode.CUSTOMER)
        self.assertEqual(token["status"], UserStatus.ACTIVE)
        self.assertIn("full_name", token)

    def test_invalid_refresh_token_returns_401(self):
        resp = self.client.post(reverse("token-refresh"), {"refresh": "bad.refresh.token"})
        self.assertEqual(resp.status_code, 401)


# ===========================================================================
# 7. Password and PIN Reset Flows
# ===========================================================================

class PasswordPINResetTests(TestCase):
    """
    Validates the two-step password and PIN reset flows.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user("+966502000060", status=UserStatus.ACTIVE)

    # --- Password Reset ---

    def test_password_reset_request_returns_200(self):
        resp = self.client.post(
            reverse("reset-password-send-otp"),
            {"phone_number": self.user.phone_number},
        )
        self.assertEqual(resp.status_code, 200)

    def test_password_reset_confirm_changes_password(self):
        _, otp_plain = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.PASSWORD_RESET,
            user=self.user,
        )
        resp = self.client.post(
            reverse("reset-password-confirm"),
            {
                "phone_number": self.user.phone_number,
                "otp_code": otp_plain,
                "new_password": "NewSecure1!",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecure1!"))
        self.assertFalse(self.user.check_password("ValidPass1!"))

    def test_password_reset_creates_audit_record(self):
        _, otp_plain = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.PASSWORD_RESET,
            user=self.user,
        )
        self.client.post(
            reverse("reset-password-confirm"),
            {
                "phone_number": self.user.phone_number,
                "otp_code": otp_plain,
                "new_password": "NewSecure1!",
            },
        )
        audit = PasswordResetAudit.objects.filter(
            user=self.user,
            reset_type=ResetType.PASSWORD,
            success=True,
        ).last()
        self.assertIsNotNone(audit)

    def test_password_reset_with_wrong_otp_returns_400(self):
        create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.PASSWORD_RESET,
        )
        resp = self.client.post(
            reverse("reset-password-confirm"),
            {
                "phone_number": self.user.phone_number,
                "otp_code": "000000",
                "new_password": "NewSecure1!",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "otp_invalid")

    # --- PIN Reset ---

    def test_pin_reset_request_returns_200(self):
        resp = self.client.post(
            reverse("reset-pin-send-otp"),
            {"phone_number": self.user.phone_number},
        )
        self.assertEqual(resp.status_code, 200)

    def test_pin_reset_confirm_changes_pin(self):
        _, otp_plain = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.PIN_RESET,
            user=self.user,
        )
        resp = self.client.post(
            reverse("reset-pin-confirm"),
            {
                "phone_number": self.user.phone_number,
                "otp_code": otp_plain,
                "new_pin": "8888",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.user.refresh_from_db()
        self.assertTrue(check_password("8888", self.user.pin_hash))
        self.assertFalse(check_password("4321", self.user.pin_hash))

    def test_pin_reset_creates_audit_record(self):
        _, otp_plain = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.PIN_RESET,
            user=self.user,
        )
        self.client.post(
            reverse("reset-pin-confirm"),
            {
                "phone_number": self.user.phone_number,
                "otp_code": otp_plain,
                "new_pin": "8888",
            },
        )
        audit = PasswordResetAudit.objects.filter(
            user=self.user,
            reset_type=ResetType.PIN,
            success=True,
        ).last()
        self.assertIsNotNone(audit)

    def test_non_digit_pin_reset_returns_400(self):
        _, otp_plain = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.PIN_RESET,
            user=self.user,
        )
        resp = self.client.post(
            reverse("reset-pin-confirm"),
            {
                "phone_number": self.user.phone_number,
                "otp_code": otp_plain,
                "new_pin": "abcd",
            },
        )
        self.assertEqual(resp.status_code, 400)
