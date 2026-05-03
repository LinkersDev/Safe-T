"""
Integration tests for security auth endpoints.

Uses Django TestClient + APIClient (no real DB — SQLite in test settings).
Run:  python manage.py test apps.security.tests.test_views --settings=config.settings.dev
"""
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import Role, User
from apps.users.constants import RoleCode, UserStatus
from apps.users.models import Permission, RolePermission

from apps.security.constants import OTPRequestType, OTPStatus
from apps.security.models import OTPRequest
from apps.security.services import create_otp


def _make_active_customer(phone="+966501234580"):
    role, _ = Role.objects.get_or_create(
        code=RoleCode.CUSTOMER,
        defaults={"name": "Customer", "is_staff_role": False, "is_system_role": True},
    )
    user = User(
        phone_number=phone,
        phone_number_normalized=phone,
        full_name="Integration Tester",
        role=role,
        status=UserStatus.ACTIVE,
        is_active=True,
    )
    user.set_password("TestPass123!")
    user.pin_hash = make_password("1234")
    user.save()
    return user


class SendRegistrationOTPViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("register-send-otp")

    def test_valid_new_phone_returns_200(self):
        resp = self.client.post(self.url, {"phone_number": "+966501234581"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("message", resp.data)

    def test_existing_phone_returns_409(self):
        _make_active_customer("+966501234582")
        resp = self.client.post(self.url, {"phone_number": "+966501234582"})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["code"], "phone_taken")

    def test_invalid_phone_returns_400(self):
        resp = self.client.post(self.url, {"phone_number": "not-a-phone"})
        self.assertEqual(resp.status_code, 400)


class CompleteRegistrationViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("register-complete")
        self.phone = "+966501234583"

    def _get_otp(self):
        _, otp_plain = create_otp(
            phone=self.phone,
            request_type=OTPRequestType.REGISTRATION,
        )
        return otp_plain

    def test_valid_registration_creates_pending_user(self):
        otp = self._get_otp()
        resp = self.client.post(self.url, {
            "phone_number": self.phone,
            "otp_code": otp,
            "full_name": "New User",
            "password": "TestPass123!",
            "pin": "1234",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["user"]["status"], UserStatus.PENDING_VERIFICATION)

    def test_wrong_otp_returns_400(self):
        self._get_otp()
        resp = self.client.post(self.url, {
            "phone_number": self.phone,
            "otp_code": "000000",
            "full_name": "New User",
            "password": "TestPass123!",
            "pin": "1234",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "otp_invalid")

    def test_non_numeric_pin_returns_400(self):
        otp = self._get_otp()
        resp = self.client.post(self.url, {
            "phone_number": self.phone,
            "otp_code": otp,
            "full_name": "New User",
            "password": "TestPass123!",
            "pin": "abcd",
        })
        self.assertEqual(resp.status_code, 400)


class SendLoginOTPViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("login-send-otp")

    def test_always_returns_200_generic_message(self):
        # Unknown phone
        resp = self.client.post(self.url, {"phone_number": "+966500000001"})
        self.assertEqual(resp.status_code, 200)

    def test_known_phone_also_returns_200(self):
        _make_active_customer("+966501234584")
        resp = self.client.post(self.url, {"phone_number": "+966501234584"})
        self.assertEqual(resp.status_code, 200)


class LoginViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("login")
        self.user = _make_active_customer("+966501234585")

    def _get_login_otp(self):
        _, otp_plain = create_otp(
            phone=self.user.phone_number,
            request_type=OTPRequestType.LOGIN,
            user=self.user,
        )
        return otp_plain

    def test_valid_password_login_returns_tokens(self):
        otp = self._get_login_otp()
        resp = self.client.post(self.url, {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "TestPass123!",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertIn("permissions", resp.data)
        self.assertIn("role", resp.data["user"])

    def test_login_returns_role_permissions(self):
        perm, _ = Permission.objects.get_or_create(
            code="view_all_users",
            defaults={"name": "View All Users", "module": "users"},
        )
        RolePermission.objects.get_or_create(role=self.user.role, permission=perm)
        otp = self._get_login_otp()
        resp = self.client.post(self.url, {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "TestPass123!",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("view_all_users", resp.data["permissions"])

    def test_valid_pin_login_returns_tokens(self):
        otp = self._get_login_otp()
        resp = self.client.post(self.url, {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "pin": "1234",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)

    def test_wrong_password_returns_401(self):
        otp = self._get_login_otp()
        resp = self.client.post(self.url, {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "WrongPass999!",
        })
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data.get("code"), "wrong_password")

    def test_wrong_otp_returns_400(self):
        self._get_login_otp()
        resp = self.client.post(self.url, {
            "phone_number": self.user.phone_number,
            "otp_code": "000000",
            "password": "TestPass123!",
        })
        self.assertEqual(resp.status_code, 400)

    def test_blocked_user_returns_403(self):
        self.user.status = UserStatus.BLOCKED
        self.user.save()
        otp = self._get_login_otp()
        resp = self.client.post(self.url, {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "TestPass123!",
        })
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data["code"], "account_blocked")

    def test_locked_user_returns_403(self):
        self.user.is_active = False
        self.user.save()
        otp = self._get_login_otp()
        resp = self.client.post(self.url, {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
            "password": "TestPass123!",
        })
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data["code"], "account_locked")

    def test_missing_credential_returns_400(self):
        otp = self._get_login_otp()
        resp = self.client.post(self.url, {
            "phone_number": self.user.phone_number,
            "otp_code": otp,
        })
        self.assertEqual(resp.status_code, 400)
