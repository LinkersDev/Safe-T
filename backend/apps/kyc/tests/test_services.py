"""
Unit tests for KYC services and the ledger KYC guard.

Covered:
  1. upload_kyc_document → sets user.kyc_status = PENDING
  2. approve_user_kyc    → sets kyc_status = APPROVED
  3. reject_user_kyc     → sets kyc_status = REJECTED
  4. re-upload after rejection → kyc_status back to PENDING
  5. KYC guard in post_transaction blocks non-APPROVED users
  6. KYC guard allows APPROVED users
  7. approve_kyc_document / reject_kyc_document
  8. Double-approve raises KycAlreadyApprovedError
  9. Reject non-PENDING KYC raises KycNotPendingError
"""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.accounts.constants import AccountStatus
from apps.accounts.models import Account, Currency
from apps.ledger.constants import TransactionType
from apps.ledger.exceptions import KYCNotApprovedError
from apps.ledger.services import post_transaction
from apps.users.constants import KycStatus, UserStatus
from apps.users.models import User

from apps.kyc.constants import KycDocumentStatus, KycDocumentType
from apps.kyc.exceptions import KycAlreadyApprovedError, KycNotPendingError
from apps.kyc.models import KycDocument
from apps.kyc.services import (
    approve_kyc_document,
    approve_user_kyc,
    reject_kyc_document,
    reject_user_kyc,
    upload_kyc_document,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _currency():
    return Currency.objects.get_or_create(
        code="USD",
        defaults={"name": "US Dollar", "symbol": "$", "decimal_places": 2},
    )[0]


def _user(phone="+966500010001", kyc_status=KycStatus.NOT_SUBMITTED, status=UserStatus.ACTIVE):
    return User.objects.create_user(
        phone_number=phone, password="TestPass1!", status=status, kyc_status=kyc_status
    )


def _staff(phone="+966500010099"):
    return User.objects.create_user(
        phone_number=phone, password="StaffPass1!", status=UserStatus.ACTIVE,
        kyc_status=KycStatus.APPROVED,
    )


def _account(user, balance=Decimal("500.00")):
    return Account.objects.create(
        user=user,
        currency=_currency(),
        account_number=f"{7000 + Account.objects.count():016d}",
        account_name=f"Acct {user.phone_number}",
        status=AccountStatus.ACTIVE,
        available_balance=balance,
        ledger_balance=balance,
    )


def _fake_file(name="id.jpg"):
    return SimpleUploadedFile(name, b"fake-image-data", content_type="image/jpeg")


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------

class UploadDocumentTest(TestCase):

    def test_upload_creates_document(self):
        user = _user()
        doc = upload_kyc_document(
            user=user, document_type=KycDocumentType.NATIONAL_ID, file=_fake_file()
        )
        self.assertIsInstance(doc, KycDocument)
        self.assertEqual(doc.document_type, KycDocumentType.NATIONAL_ID)
        self.assertEqual(doc.status, KycDocumentStatus.PENDING)

    def test_upload_sets_user_kyc_status_pending(self):
        user = _user(kyc_status=KycStatus.NOT_SUBMITTED)
        upload_kyc_document(user=user, document_type=KycDocumentType.PASSPORT, file=_fake_file())
        user.refresh_from_db()
        self.assertEqual(user.kyc_status, KycStatus.PENDING)

    def test_upload_does_not_downgrade_approved(self):
        """Uploading a doc while already APPROVED must NOT downgrade kyc_status."""
        user = _user(kyc_status=KycStatus.APPROVED)
        upload_kyc_document(user=user, document_type=KycDocumentType.SELFIE, file=_fake_file())
        user.refresh_from_db()
        self.assertEqual(user.kyc_status, KycStatus.APPROVED)

    def test_upload_after_rejection_sets_pending(self):
        """After a REJECTED KYC, uploading a new doc resets status to PENDING."""
        user = _user(kyc_status=KycStatus.REJECTED)
        upload_kyc_document(user=user, document_type=KycDocumentType.NATIONAL_ID, file=_fake_file())
        user.refresh_from_db()
        self.assertEqual(user.kyc_status, KycStatus.PENDING)


# ---------------------------------------------------------------------------
# Approve / reject KYC (user-level)
# ---------------------------------------------------------------------------

class ApproveRejectKycTest(TestCase):

    def setUp(self):
        self.staff = _staff()
        self.user = _user(kyc_status=KycStatus.PENDING)

    def test_approve_sets_approved(self):
        result = approve_user_kyc(user_id=self.user.pk, reviewed_by=self.staff)
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, KycStatus.APPROVED)
        self.assertEqual(result.kyc_status, KycStatus.APPROVED)

    def test_reject_sets_rejected(self):
        reject_user_kyc(user_id=self.user.pk, reviewed_by=self.staff, reason="Documents blurry.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, KycStatus.REJECTED)

    def test_double_approve_raises(self):
        approve_user_kyc(user_id=self.user.pk, reviewed_by=self.staff)
        with self.assertRaises(KycAlreadyApprovedError):
            approve_user_kyc(user_id=self.user.pk, reviewed_by=self.staff)

    def test_reject_not_pending_raises(self):
        """Rejecting a user whose KYC is NOT_SUBMITTED raises KycNotPendingError."""
        user2 = _user(phone="+966500010002", kyc_status=KycStatus.NOT_SUBMITTED)
        with self.assertRaises(KycNotPendingError):
            reject_user_kyc(user_id=user2.pk, reviewed_by=self.staff, reason="Some reason.")

    def test_reupload_after_rejection_and_approve(self):
        """Full rejection → re-upload → approval cycle."""
        reject_user_kyc(user_id=self.user.pk, reviewed_by=self.staff, reason="Blurry.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, KycStatus.REJECTED)

        upload_kyc_document(user=self.user, document_type=KycDocumentType.NATIONAL_ID, file=_fake_file())
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, KycStatus.PENDING)

        approve_user_kyc(user_id=self.user.pk, reviewed_by=self.staff)
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, KycStatus.APPROVED)


# ---------------------------------------------------------------------------
# Document-level approve / reject
# ---------------------------------------------------------------------------

class DocumentLevelReviewTest(TestCase):

    def setUp(self):
        self.staff = _staff()
        self.user = _user(kyc_status=KycStatus.PENDING)
        self.doc = upload_kyc_document(
            user=self.user, document_type=KycDocumentType.NATIONAL_ID, file=_fake_file()
        )

    def test_approve_document(self):
        doc = approve_kyc_document(doc_id=self.doc.pk, reviewed_by=self.staff, notes="Clear scan.")
        self.assertEqual(doc.status, KycDocumentStatus.APPROVED)
        self.assertEqual(doc.reviewed_by, self.staff)
        self.assertIsNotNone(doc.reviewed_at)

    def test_reject_document(self):
        doc = reject_kyc_document(
            doc_id=self.doc.pk, reviewed_by=self.staff, reason="Photo is blurry."
        )
        self.assertEqual(doc.status, KycDocumentStatus.REJECTED)
        self.assertEqual(doc.rejection_reason, "Photo is blurry.")


# ---------------------------------------------------------------------------
# KYC guard in post_transaction
# ---------------------------------------------------------------------------

class LedgerKycGuardTest(TestCase):
    """
    Verifies that _assert_kyc_approved() inside post_transaction() blocks
    users without APPROVED KYC and allows users who are APPROVED.
    """

    def setUp(self):
        self.currency = _currency()

    def _tx(self, src_user, dst_user):
        src = _account(src_user, Decimal("500.00"))
        dst = _account(dst_user, Decimal("0.00"))
        return post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("100.00"),
            source_account=src,
            destination_account=dst,
            customer=src_user,
        )

    def test_not_submitted_blocked(self):
        user = _user(phone="+966500011001", kyc_status=KycStatus.NOT_SUBMITTED)
        receiver = _user(phone="+966500011002", kyc_status=KycStatus.APPROVED)
        with self.assertRaises(KYCNotApprovedError):
            self._tx(user, receiver)

    def test_pending_kyc_blocked(self):
        user = _user(phone="+966500011003", kyc_status=KycStatus.PENDING)
        receiver = _user(phone="+966500011004", kyc_status=KycStatus.APPROVED)
        with self.assertRaises(KYCNotApprovedError):
            self._tx(user, receiver)

    def test_rejected_kyc_blocked(self):
        user = _user(phone="+966500011005", kyc_status=KycStatus.REJECTED)
        receiver = _user(phone="+966500011006", kyc_status=KycStatus.APPROVED)
        with self.assertRaises(KYCNotApprovedError):
            self._tx(user, receiver)

    def test_approved_kyc_allowed(self):
        user = _user(phone="+966500011007", kyc_status=KycStatus.APPROVED)
        receiver = _user(phone="+966500011008", kyc_status=KycStatus.APPROVED)
        tx = self._tx(user, receiver)
        from apps.ledger.constants import TransactionStatus
        self.assertEqual(tx.status, TransactionStatus.COMPLETED)

    def test_no_customer_skips_guard(self):
        """post_transaction with customer=None skips the KYC guard."""
        src_user = _user(phone="+966500011009", kyc_status=KycStatus.NOT_SUBMITTED)
        dst_user = _user(phone="+966500011010", kyc_status=KycStatus.NOT_SUBMITTED)
        src = _account(src_user, Decimal("500.00"))
        dst = _account(dst_user, Decimal("0.00"))
        # Should NOT raise — customer=None bypasses the guard (e.g. system operations)
        tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("100.00"),
            source_account=src,
            destination_account=dst,
            customer=None,
        )
        from apps.ledger.constants import TransactionStatus
        self.assertEqual(tx.status, TransactionStatus.COMPLETED)
