"""
Integration tests for KYC API endpoints.

Covered:
  1. GET  /api/kyc/status/          → returns status + documents
  2. POST /api/kyc/upload/          → creates document, sets kyc_status=PENDING
  3. IsKYCApproved permission class → blocks non-APPROVED from financial ops
  4. POST /api/staff/kyc/users/{id}/approve/  → approves KYC
  5. POST /api/staff/kyc/users/{id}/reject/   → rejects KYC
  6. GET  /api/staff/kyc/pending/             → lists pending users
  7. POST /api/staff/kyc/documents/{id}/approve/ & reject
  8. Reject + re-upload flow via API
"""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.constants import AccountStatus
from apps.accounts.models import Account, Currency
from apps.users.constants import KycStatus, UserStatus
from apps.users.models import Permission, Role, RolePermission, User

from apps.kyc.constants import KycDocumentType
from apps.kyc.models import KycDocument


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _currency():
    return Currency.objects.get_or_create(
        code="USD",
        defaults={"name": "US Dollar", "symbol": "$", "decimal_places": 2},
    )[0]


def _user(phone, kyc_status=KycStatus.NOT_SUBMITTED, status=UserStatus.ACTIVE):
    return User.objects.create_user(
        phone_number=phone, password="TestPass1!", status=status, kyc_status=kyc_status
    )


def _staff_with_kyc_perm(phone="+966599901001"):
    role, _ = Role.objects.get_or_create(code="ADMIN", defaults={"name": "Admin"})
    perm, _ = Permission.objects.get_or_create(
        code="review_kyc", defaults={"name": "Review KYC"}
    )
    RolePermission.objects.get_or_create(role=role, permission=perm)
    user = User.objects.create_user(
        phone_number=phone, password="StaffPass1!", status=UserStatus.ACTIVE,
        kyc_status=KycStatus.APPROVED,
    )
    user.role = role
    user.save(update_fields=["role"])
    return user


def _bearer(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")
    return client


def _fake_file(name="id.jpg"):
    return SimpleUploadedFile(name, b"fake-image-data", content_type="image/jpeg")


def _account(user, balance=Decimal("500.00")):
    return Account.objects.create(
        user=user,
        currency=_currency(),
        account_number=f"{8000 + Account.objects.count():016d}",
        account_name=f"Acct {user.phone_number}",
        status=AccountStatus.ACTIVE,
        available_balance=balance,
        ledger_balance=balance,
    )


# ---------------------------------------------------------------------------
# Test: Customer KYC status endpoint
# ---------------------------------------------------------------------------

class KycStatusViewTest(TestCase):

    def setUp(self):
        self.user = _user("+966500020001")
        self.client = _bearer(self.user)

    def test_returns_kyc_status(self):
        resp = self.client.get("/api/kyc/status/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("kyc_status", resp.json())
        self.assertEqual(resp.json()["kyc_status"], KycStatus.NOT_SUBMITTED)

    def test_returns_documents_list(self):
        resp = self.client.get("/api/kyc/status/")
        self.assertIn("documents", resp.json())
        self.assertIsInstance(resp.json()["documents"], list)

    def test_requires_authentication(self):
        resp = APIClient().get("/api/kyc/status/")
        self.assertEqual(resp.status_code, 401)


# ---------------------------------------------------------------------------
# Test: Document upload
# ---------------------------------------------------------------------------

class KycUploadViewTest(TestCase):

    def setUp(self):
        self.user = _user("+966500020002")
        self.client = _bearer(self.user)

    def test_upload_creates_document(self):
        resp = self.client.post(
            "/api/kyc/upload/",
            {"document_type": KycDocumentType.NATIONAL_ID, "file": _fake_file()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(KycDocument.objects.filter(user=self.user).count(), 1)

    def test_upload_sets_pending(self):
        self.client.post(
            "/api/kyc/upload/",
            {"document_type": KycDocumentType.PASSPORT, "file": _fake_file()},
            format="multipart",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, KycStatus.PENDING)

    def test_invalid_document_type_rejected(self):
        resp = self.client.post(
            "/api/kyc/upload/",
            {"document_type": "UNKNOWN_TYPE", "file": _fake_file()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)

    def test_missing_file_rejected(self):
        resp = self.client.post(
            "/api/kyc/upload/",
            {"document_type": KycDocumentType.SELFIE},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# Test: IsKYCApproved permission on payment execute endpoints
# ---------------------------------------------------------------------------

class KycPermissionOnPaymentsTest(TestCase):
    """
    Financial execute endpoints must return 403 for non-APPROVED users
    even when they are otherwise authenticated and ACTIVE.
    """

    def setUp(self):
        self.currency = _currency()
        # Payer without KYC approval
        self.payer_not_approved = _user("+966500020010", kyc_status=KycStatus.PENDING)
        self.client_na = _bearer(self.payer_not_approved)

        # KYC-approved payer
        self.payer_approved = _user("+966500020011", kyc_status=KycStatus.APPROVED)
        self.client_ok = _bearer(self.payer_approved)

        self.payer_account = _account(self.payer_approved, Decimal("500.00"))

    def test_transfer_execute_blocked_without_kyc(self):
        resp = self.client_na.post(
            "/api/payments/transfer/",
            {"destination_account_number": "0000000000000001", "amount": "100.00", "otp_code": "000000"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_qr_pay_blocked_without_kyc(self):
        resp = self.client_na.post(
            "/api/payments/qr/pay/",
            {"qr_token": "dummy", "otp_code": "000000"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_bill_pay_blocked_without_kyc(self):
        resp = self.client_na.post(
            "/api/payments/bill/pay/",
            {"provider_code": "ELEC", "service_number": "123", "amount": "50", "otp_code": "000000"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_not_submitted_also_blocked(self):
        """NOT_SUBMITTED (default) must be blocked just like PENDING."""
        user_ns = _user("+966500020012", kyc_status=KycStatus.NOT_SUBMITTED)
        client = _bearer(user_ns)
        resp = client.post(
            "/api/payments/transfer/",
            {"destination_account_number": "0", "amount": "10", "otp_code": "000000"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_approved_user_gets_past_permission_check(self):
        """Approved user passes the permission check (may fail for other reasons like OTP)."""
        # Issue an OTP first
        from apps.security.services import create_otp
        from apps.security.constants import OTPRequestType
        _, otp = create_otp(
            phone=self.payer_approved.phone_number,
            request_type=OTPRequestType.TRANSFER,
            user=self.payer_approved,
        )
        # Try to transfer — should NOT be 403; may be 400/404 for missing dest
        resp = self.client_ok.post(
            "/api/payments/transfer/",
            {
                "destination_account_number": "9999999999999999",
                "amount": "100.00",
                "otp_code": otp,
            },
            format="json",
        )
        self.assertNotEqual(resp.status_code, 403, "APPROVED user must pass permission check")


# ---------------------------------------------------------------------------
# Test: Staff KYC approval/rejection
# ---------------------------------------------------------------------------

class StaffKycActionsTest(TestCase):

    def setUp(self):
        self.staff = _staff_with_kyc_perm()
        self.staff_client = _bearer(self.staff)
        self.user = _user("+966500020020", kyc_status=KycStatus.PENDING)
        from apps.kyc.services import upload_kyc_document
        upload_kyc_document(user=self.user, document_type=KycDocumentType.NATIONAL_ID, file=_fake_file())

    def test_pending_queue_lists_user(self):
        resp = self.staff_client.get("/api/staff/kyc/pending/")
        self.assertEqual(resp.status_code, 200)
        ids = [u["id"] for u in resp.json()]
        self.assertIn(self.user.pk, ids)

    def test_approve_user_kyc(self):
        resp = self.staff_client.post(f"/api/staff/kyc/users/{self.user.pk}/approve/")
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, KycStatus.APPROVED)

    def test_reject_user_kyc(self):
        resp = self.staff_client.post(
            f"/api/staff/kyc/users/{self.user.pk}/reject/",
            {"reason": "Document is expired."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, KycStatus.REJECTED)

    def test_reject_requires_reason(self):
        resp = self.staff_client.post(
            f"/api/staff/kyc/users/{self.user.pk}/reject/",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_double_approve_returns_409(self):
        self.staff_client.post(f"/api/staff/kyc/users/{self.user.pk}/approve/")
        resp = self.staff_client.post(f"/api/staff/kyc/users/{self.user.pk}/approve/")
        self.assertEqual(resp.status_code, 409)

    def test_user_documents_list(self):
        resp = self.staff_client.get(f"/api/staff/kyc/users/{self.user.pk}/documents/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_staff_without_permission_blocked(self):
        """A user with no review_kyc permission cannot access staff KYC endpoints."""
        no_perm_user = User.objects.create_user(
            phone_number="+966599901099", password="P!", status=UserStatus.ACTIVE,
            kyc_status=KycStatus.APPROVED,
        )
        client = _bearer(no_perm_user)
        resp = client.get("/api/staff/kyc/pending/")
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Test: Document-level approve / reject via API
# ---------------------------------------------------------------------------

class StaffDocumentReviewTest(TestCase):

    def setUp(self):
        self.staff = _staff_with_kyc_perm("+966599901002")
        self.staff_client = _bearer(self.staff)
        self.user = _user("+966500020030", kyc_status=KycStatus.PENDING)
        from apps.kyc.services import upload_kyc_document
        self.doc = upload_kyc_document(
            user=self.user, document_type=KycDocumentType.SELFIE, file=_fake_file()
        )

    def test_approve_document(self):
        resp = self.staff_client.post(
            f"/api/staff/kyc/documents/{self.doc.pk}/approve/",
            {"notes": "Looks good."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, "APPROVED")

    def test_reject_document(self):
        resp = self.staff_client.post(
            f"/api/staff/kyc/documents/{self.doc.pk}/reject/",
            {"reason": "Photo not clear."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, "REJECTED")
        self.assertEqual(self.doc.rejection_reason, "Photo not clear.")


# ---------------------------------------------------------------------------
# Test: Full reject → re-upload → approve cycle via API
# ---------------------------------------------------------------------------

class KycFullCycleTest(TestCase):
    """End-to-end: reject KYC, re-upload document, approve KYC."""

    def setUp(self):
        self.staff = _staff_with_kyc_perm("+966599901003")
        self.staff_client = _bearer(self.staff)
        self.user = _user("+966500020040", kyc_status=KycStatus.PENDING)
        self.user_client = _bearer(self.user)
        from apps.kyc.services import upload_kyc_document
        upload_kyc_document(user=self.user, document_type=KycDocumentType.NATIONAL_ID, file=_fake_file())

    def test_reject_reupload_approve_flow(self):
        # 1. Staff rejects KYC
        resp = self.staff_client.post(
            f"/api/staff/kyc/users/{self.user.pk}/reject/",
            {"reason": "Wrong document type uploaded."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, KycStatus.REJECTED)

        # 2. Customer re-uploads (new document)
        resp = self.user_client.post(
            "/api/kyc/upload/",
            {"document_type": KycDocumentType.PASSPORT, "file": _fake_file("passport.jpg")},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, KycStatus.PENDING)

        # 3. Staff approves
        resp = self.staff_client.post(f"/api/staff/kyc/users/{self.user.pk}/approve/")
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, KycStatus.APPROVED)

        # 4. User now has 2 documents on record
        self.assertEqual(KycDocument.objects.filter(user=self.user).count(), 2)
