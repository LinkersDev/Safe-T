"""
End-to-end system validation for SafeT backend.

Wraps all scenarios inside a Django TestCase so the test database (SQLite)
is automatically created, migrated, and torn down.

Usage:
    python manage.py test apps.users.management.commands.validate_e2e --settings=config.settings.test -v 2

Each step prints:
  REQUEST:  method + URL + body summary
  RESPONSE: status + key fields
  VERIFY:   DB-level assertion results
"""
import json
import sys
from decimal import Decimal

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Full end-to-end system validation (runs inside test DB)."

    def handle(self, *args, **options):
        # Delegate to the test runner so the DB is properly set up
        from django.test.utils import get_runner
        from django.conf import settings as django_settings

        TestRunner = get_runner(django_settings)
        test_runner = TestRunner(verbosity=2)

        from django.test.loader import TestLoader
        loader = TestLoader()
        suite = loader.loadTestsFromName(
            "apps.users.management.commands.validate_e2e.E2EValidationTest"
        )
        result = test_runner.run_suite(suite)
        if result.wasSuccessful():
            self.stdout.write("\n[RESULT] End-to-end system is working correctly.\n")
        else:
            self.stdout.write(f"\n[RESULT] {len(result.failures) + len(result.errors)} check(s) FAILED.\n")
            sys.exit(1)


# ============================================================
#  The actual test — import-accessible for TestLoader
# ============================================================

import json
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient


def _p(label, value):
    """Print a labelled line during test execution."""
    print(f"  {label}: {value}")


def _req(method, url, body=None):
    summary = f"{method} {url}"
    if body:
        trimmed = {k: v for k, v in body.items() if k not in ("password", "pin", "otp_code")}
        summary += f"  body={json.dumps(trimmed)}"
    print(f"\n  >> {summary}")


def _resp(resp, keys=None):
    try:
        data = resp.json()
    except Exception:
        data = {}
    if keys:
        data = {k: data[k] for k in keys if k in data}
    print(f"  HTTP {resp.status_code}  {json.dumps(data, default=str)[:400]}")


class E2EValidationTest(TestCase):

    maxDiff = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _bearer(self, token):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return c

    def _patch_otp(self, phone, request_type, purpose_ref, new_code):
        """Replace a pending OTP hash with a known code for testing."""
        from apps.security.models import OTPRequest
        from django.contrib.auth.hashers import make_password
        rec = OTPRequest.objects.filter(
            phone_number=phone,
            request_type=request_type,
            purpose_reference=purpose_ref,
        ).latest("created_at")
        rec.otp_hash = make_password(new_code)
        rec.save(update_fields=["otp_hash"])

    def _balance(self, account_id):
        from apps.accounts.models import Account
        a = Account.objects.get(pk=account_id)
        return a.available_balance, a.ledger_balance

    def _entries_balanced(self, tx_ref):
        from apps.ledger.constants import EntryType
        from apps.ledger.models import Transaction, TransactionEntry
        tx = Transaction.objects.get(reference_number=tx_ref)
        entries = list(TransactionEntry.objects.filter(transaction=tx))
        debit  = sum(e.amount for e in entries if e.entry_type in EntryType.DEBIT_TYPES)
        credit = sum(e.amount for e in entries if e.entry_type in EntryType.CREDIT_TYPES)
        return debit == credit, debit, credit

    # ------------------------------------------------------------------
    # setUp — seed prerequisite data
    # ------------------------------------------------------------------

    def setUp(self):
        from apps.accounts.constants import AccountStatus
        from apps.accounts.models import Account, Currency
        from apps.payments.models import BillProvider, MerchantProfile
        from apps.users.constants import UserStatus
        from apps.users.models import Permission, Role, RolePermission, User

        self.currency, _ = Currency.objects.get_or_create(
            code="USD",
            defaults={"name": "US Dollar", "symbol": "$", "decimal_places": 2},
        )

        # Admin staff — role already seeded by migration (look up by code)
        admin_role = Role.objects.get(code="ADMIN")
        for perm_code, perm_name in [
            ("approve_user",        "Approve User"),
            ("view_all_transactions", "View All Transactions"),
            ("reverse_transaction", "Reverse Transaction"),
            ("manage_system",       "Manage System"),
            ("review_kyc",          "Review KYC"),
        ]:
            perm, _ = Permission.objects.get_or_create(code=perm_code, defaults={"name": perm_name})
            RolePermission.objects.get_or_create(role=admin_role, permission=perm)

        from apps.users.constants import KycStatus
        self.staff = User.objects.create_user(
            phone_number="+966599000001",
            password="StaffPass1!",
            status=UserStatus.ACTIVE,
            kyc_status=KycStatus.APPROVED,
        )
        self.staff.role = admin_role
        self.staff.save(update_fields=["role"])

        from rest_framework_simplejwt.tokens import RefreshToken
        self.staff_client = self._bearer(str(RefreshToken.for_user(self.staff).access_token))

        # Merchant — role already seeded
        merchant_role = Role.objects.get(code="MERCHANT_CUSTOMER")
        self.merchant_user = User.objects.create_user(
            phone_number="+966599000002",
            password="Merchant1!",
            status=UserStatus.ACTIVE,
            kyc_status=KycStatus.APPROVED,
        )
        self.merchant_user.role = merchant_role
        self.merchant_user.save(update_fields=["role"])

        self.merchant_account = Account.objects.create(
            user=self.merchant_user,
            currency=self.currency,
            account_number="0000000000000010",
            account_name="Merchant Settlement",
            status=AccountStatus.ACTIVE,
            available_balance=Decimal("0"),
            ledger_balance=Decimal("0"),
        )
        MerchantProfile.objects.create(
            user=self.merchant_user,
            settlement_account=self.merchant_account,
            business_name="SafeT Shop",
            business_type="Retail",
            registration_number="SAF-001",
            contact_phone="+966599000002",
        )
        self.merchant_client = self._bearer(str(RefreshToken.for_user(self.merchant_user).access_token))

        # Bill provider
        self.provider_account = Account.objects.create(
            user=self.staff,
            currency=self.currency,
            account_number="0000000000000020",
            account_name="Electricity Corp",
            status=AccountStatus.ACTIVE,
            available_balance=Decimal("0"),
            ledger_balance=Decimal("0"),
        )
        self.bill_provider = BillProvider.objects.create(
            code="ELEC-USD",
            name="Somalia Electricity",
            service_type="ELECTRICITY",
            provider_account=self.provider_account,
        )

        self.customer_phone = "+966512345678"

    # ==================================================================
    #  THE SINGLE E2E TEST
    # ==================================================================

    def test_full_e2e_flow(self):
        print("\n" + "="*60)
        print("  SafeT End-to-End System Validation")
        print("="*60)

        user_id = self._scenario_registration()
        self._scenario_staff_approval(user_id)
        self._scenario_kyc(user_id)
        account_id = self._scenario_fund_account(user_id)
        access_token = self._scenario_login()
        self._scenario_transfer(access_token, account_id)
        self._scenario_qr_payment(access_token, account_id)
        self._scenario_bill_payment(access_token, account_id)

        print("\n" + "="*60)
        print("[RESULT] End-to-end system is working correctly.")
        print("="*60 + "\n")

    # ------------------------------------------------------------------
    # Scenario 1 — Registration
    # ------------------------------------------------------------------

    def _scenario_registration(self):
        print("\n--- STEP 1: User Registration ---")

        client = APIClient()
        phone = self.customer_phone

        # 1a: Send registration OTP
        _req("POST", "/api/auth/register/", {"phone_number": phone})
        resp = client.post("/api/auth/register/", {"phone_number": phone}, format="json")
        _resp(resp, ["detail"])
        self.assertEqual(resp.status_code, 200, f"1a: Expected 200, got {resp.status_code}")
        print("  [PASS] 1a: Registration OTP sent -> 200")

        # Patch OTP to a known code
        self._patch_otp(phone, "REGISTRATION", "", "123456")

        # 1b: Complete registration
        _req("POST", "/api/auth/register/complete/", {"phone_number": phone})
        payload = {
            "phone_number": phone,
            "otp_code": "123456",
            "full_name": "Test Customer",
            "password": "SecurePass1!",
            "pin": "123456",
        }
        resp = client.post("/api/auth/register/complete/", payload, format="json")
        _resp(resp, ["detail", "user_id", "status"])
        self.assertEqual(resp.status_code, 201, f"1b: Expected 201, got {resp.status_code} body={resp.json()}")
        print("  [PASS] 1b: Registration completed -> 201")

        # 1c: DB state — PENDING_VERIFICATION
        from apps.users.models import User
        from apps.users.constants import UserStatus
        user = User.objects.get(phone_number=phone)
        self.assertEqual(user.status, UserStatus.PENDING_VERIFICATION)
        print(f"  [PASS] 1c: User status = PENDING_VERIFICATION (user_id={user.pk})")

        # 1d: OTP not reusable
        _req("POST", "/api/auth/register/complete/ [replay]")
        resp2 = client.post("/api/auth/register/complete/", payload, format="json")
        self.assertIn(resp2.status_code, (400, 409), f"1d: Expected 400/409, got {resp2.status_code}")
        print(f"  [PASS] 1d: OTP not reusable -> {resp2.status_code}")

        return user.pk

    # ------------------------------------------------------------------
    # Scenario 2 — Staff Approval
    # ------------------------------------------------------------------

    def _scenario_staff_approval(self, user_id):
        print("\n--- STEP 2: Staff Approval ---")

        _req("POST", f"/api/staff/users/{user_id}/approve/")
        resp = self.staff_client.post(f"/api/staff/users/{user_id}/approve/", format="json")
        _resp(resp, ["detail", "status"])
        self.assertEqual(resp.status_code, 200, f"2a: Expected 200, got {resp.status_code} body={resp.json()}")
        print("  [PASS] 2a: Approve user -> 200")

        from apps.users.models import User
        from apps.users.constants import UserStatus
        user = User.objects.get(pk=user_id)
        self.assertEqual(user.status, UserStatus.ACTIVE)
        print("  [PASS] 2b: User status = ACTIVE in DB")

        from apps.accounts.models import Account
        account = Account.objects.filter(user_id=user_id).first()
        self.assertIsNotNone(account, "Account must be auto-created on approval")
        print(f"  [PASS] 2c: Account auto-created | number={account.account_number}")

    # ------------------------------------------------------------------
    # Scenario 2b — KYC Flow
    # ------------------------------------------------------------------

    def _scenario_kyc(self, user_id):
        print("\n--- STEP 2b: KYC Flow ---")
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.users.constants import KycStatus

        customer_client = self._bearer(
            str(__import__("rest_framework_simplejwt.tokens", fromlist=["RefreshToken"])
                .RefreshToken.for_user(
                    __import__("apps.users.models", fromlist=["User"]).User.objects.get(pk=user_id)
                ).access_token)
        )

        # 2b-i: Upload a document
        _req("POST", "/api/kyc/upload/")
        fake_file = SimpleUploadedFile("national_id.jpg", b"fake-image-data", content_type="image/jpeg")
        resp = customer_client.post(
            "/api/kyc/upload/",
            {"document_type": "NATIONAL_ID", "file": fake_file},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201, f"2b-i: {resp.status_code} {resp.json()}")
        print("  [PASS] 2b-i: KYC document uploaded -> 201")

        # Verify kyc_status = PENDING
        from apps.users.models import User
        user = User.objects.get(pk=user_id)
        self.assertEqual(user.kyc_status, KycStatus.PENDING)
        print("  [PASS] 2b-ii: User kyc_status = PENDING after upload")

        # 2b-iii: Staff approves KYC
        _req("POST", f"/api/staff/kyc/users/{user_id}/approve/")
        resp = self.staff_client.post(f"/api/staff/kyc/users/{user_id}/approve/", format="json")
        _resp(resp, ["detail", "kyc_status"])
        self.assertEqual(resp.status_code, 200, f"2b-iii: {resp.status_code} {resp.json()}")
        print("  [PASS] 2b-iii: Staff approved KYC -> 200")

        user.refresh_from_db()
        self.assertEqual(user.kyc_status, KycStatus.APPROVED)
        print("  [PASS] 2b-iv: User kyc_status = APPROVED in DB")

    # ------------------------------------------------------------------
    # Scenario 3 — Fund Account
    # ------------------------------------------------------------------

    def _scenario_fund_account(self, user_id):
        print("\n--- STEP 3: Account Funding (DB injection) ---")

        from apps.accounts.models import Account
        account = Account.objects.get(user_id=user_id)
        Account.objects.filter(pk=account.pk).update(
            available_balance=Decimal("2000.00"),
            ledger_balance=Decimal("2000.00"),
        )
        account.refresh_from_db()

        self.assertEqual(account.available_balance, Decimal("2000.00"))
        self.assertEqual(account.ledger_balance, Decimal("2000.00"))
        self.assertGreaterEqual(account.available_balance, Decimal("0"))
        print(f"  [PASS] 3a: Account {account.account_number} funded with USD 2000.00")
        print("  [PASS] 3b: No negative balance")

        self.customer_account = account
        return account.pk

    # ------------------------------------------------------------------
    # Scenario 4 — Login
    # ------------------------------------------------------------------

    def _scenario_login(self):
        print("\n--- STEP 4: Login Flow ---")
        client = APIClient()
        phone = self.customer_phone

        # 4a: Send login OTP
        _req("POST", "/api/auth/otp/send/", {"phone_number": phone})
        resp = client.post("/api/auth/otp/send/", {"phone_number": phone}, format="json")
        _resp(resp, ["detail"])
        self.assertEqual(resp.status_code, 200, f"4a: {resp.status_code}")
        print("  [PASS] 4a: Login OTP sent -> 200")

        # Patch OTP
        self._patch_otp(phone, "LOGIN", "", "654321")

        # 4b: Login
        _req("POST", "/api/auth/login/")
        payload = {"phone_number": phone, "otp_code": "654321", "password": "SecurePass1!"}
        resp = client.post("/api/auth/login/", payload, format="json")
        _resp(resp, ["access", "refresh"])
        self.assertEqual(resp.status_code, 200, f"4b: {resp.status_code} {resp.json()}")
        print("  [PASS] 4b: Login successful -> 200")

        body = resp.json()
        access = body["access"]
        refresh = body["refresh"]
        self.assertTrue(access)
        self.assertTrue(refresh)
        print("  [PASS] 4c: Access + refresh tokens issued")

        # 4c: Token refresh
        _req("POST", "/api/auth/token/refresh/")
        resp3 = client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(resp3.status_code, 200, f"4c: {resp3.status_code}")
        print("  [PASS] 4d: Token refresh -> 200")

        # 4d: OTP not reusable
        _req("POST", "/api/auth/login/ [replay]")
        resp4 = client.post("/api/auth/login/", payload, format="json")
        self.assertIn(resp4.status_code, (400, 401), f"4d: {resp4.status_code}")
        print(f"  [PASS] 4e: Login OTP not reusable -> {resp4.status_code}")

        # 4e: LoginLog created
        from apps.security.models import LoginLog
        from apps.security.constants import LoginStatus
        log = LoginLog.objects.filter(phone_number=phone, status=LoginStatus.SUCCESS).first()
        self.assertIsNotNone(log)
        print("  [PASS] 4f: LoginLog SUCCESS record created")

        return access

    # ------------------------------------------------------------------
    # Scenario 5 — Transfer
    # ------------------------------------------------------------------

    def _scenario_transfer(self, access_token, account_id):
        print("\n--- STEP 5: Transfer Flow ---")
        client = self._bearer(access_token)

        from apps.users.models import User
        user = User.objects.get(accounts__pk=account_id)
        balance_before, _ = self._balance(account_id)
        dest_balance_before, _ = self._balance(self.merchant_account.pk)

        # 5a: Request OTP
        _req("POST", "/api/payments/transfer/otp/")
        resp = client.post("/api/payments/transfer/otp/")
        _resp(resp, ["detail"])
        self.assertEqual(resp.status_code, 200, f"5a: {resp.status_code}")
        print("  [PASS] 5a: Transfer OTP sent -> 200")

        # Patch OTP
        self._patch_otp(user.phone_number, "TRANSFER", "", "111222")

        # 5b: Execute transfer
        _req("POST", "/api/payments/transfer/", {
            "destination_account_number": self.merchant_account.account_number,
            "amount": "300.00",
        })
        idempotency_key = "e2e-transfer-001"
        payload = {
            "destination_account_number": self.merchant_account.account_number,
            "amount": "300.00",
            "otp_code": "111222",
            "idempotency_key": idempotency_key,
        }
        resp = client.post("/api/payments/transfer/", payload, format="json")
        _resp(resp, ["reference_number", "status", "amount"])
        self.assertEqual(resp.status_code, 201, f"5b: {resp.status_code} {resp.json()}")
        print("  [PASS] 5b: Transfer executed -> 201")

        tx_ref = resp.json()["reference_number"]
        self.assertEqual(resp.json()["status"], "COMPLETED")
        print("  [PASS] 5c: Transaction status = COMPLETED")

        # 5c: Source debited
        balance_after, _ = self._balance(account_id)
        self.assertEqual(balance_after, balance_before - Decimal("300.00"))
        print(f"  [PASS] 5d: Source debited USD 300 (was={balance_before} now={balance_after})")

        # 5d: Dest credited
        dest_balance_after, _ = self._balance(self.merchant_account.pk)
        self.assertEqual(dest_balance_after, dest_balance_before + Decimal("300.00"))
        print(f"  [PASS] 5e: Dest credited USD 300 (was={dest_balance_before} now={dest_balance_after})")

        # 5e: No negative
        self.assertGreaterEqual(balance_after, Decimal("0"))
        print("  [PASS] 5f: No negative balance")

        # 5f: Double-entry balanced
        balanced, debit, credit = self._entries_balanced(tx_ref)
        self.assertTrue(balanced, f"Double-entry failed: debit={debit} credit={credit}")
        print(f"  [PASS] 5g: Double-entry balanced (DEBIT={debit} == CREDIT={credit})")

        # 5g: Idempotency — replay same key, balance must not change again
        from apps.security.services import create_otp
        _, otp2 = create_otp(phone=user.phone_number, request_type="TRANSFER", user=user)
        payload2 = {**payload, "otp_code": otp2}
        resp2 = client.post("/api/payments/transfer/", payload2, format="json")
        balance_replay, _ = self._balance(account_id)
        self.assertEqual(balance_replay, balance_after,
                         f"Idempotency failed — balance changed on replay: {balance_replay}")
        print(f"  [PASS] 5h: Idempotency — replay returns same tx, balance unchanged")

    # ------------------------------------------------------------------
    # Scenario 6 — QR Payment
    # ------------------------------------------------------------------

    def _scenario_qr_payment(self, access_token, account_id):
        print("\n--- STEP 6: QR Payment Flow ---")
        payer_client = self._bearer(access_token)

        balance_before, _ = self._balance(account_id)
        merch_before, _ = self._balance(self.merchant_account.pk)

        # 6a: Generate QR
        _req("POST", "/api/merchant/qr/generate/", {"amount": "150.00"})
        resp = self.merchant_client.post(
            "/api/merchant/qr/generate/",
            {"amount": "150.00", "currency_code": "USD"},
            format="json",
        )
        _resp(resp, ["qr_token", "amount_mode", "display_amount", "status"])
        self.assertEqual(resp.status_code, 201, f"6a: {resp.status_code}")
        qr_token = resp.json()["qr_token"]
        self.assertTrue(qr_token)
        print("  [PASS] 6a: QR code generated -> 201")

        # 6b: Resolve QR
        _req("GET", f"/api/payments/qr/{qr_token[:12]}...")
        resp = payer_client.get(f"/api/payments/qr/{qr_token}/")
        _resp(resp, ["merchant_name", "display_amount", "status"])
        self.assertEqual(resp.status_code, 200, f"6b: {resp.status_code}")
        self.assertEqual(resp.json()["status"], "PENDING")
        print("  [PASS] 6b: QR resolved -> 200, status=PENDING")

        # 6c: Request OTP
        _req("POST", "/api/payments/qr/otp/")
        resp = payer_client.post("/api/payments/qr/otp/", {"qr_token": qr_token}, format="json")
        _resp(resp, ["detail"])
        self.assertEqual(resp.status_code, 200, f"6c: {resp.status_code}")
        print("  [PASS] 6c: QR OTP sent -> 200")

        from apps.users.models import User
        user = User.objects.get(accounts__pk=account_id)
        self._patch_otp(user.phone_number, "QR_PAYMENT", qr_token, "333444")

        # 6d: Execute payment
        _req("POST", "/api/payments/qr/pay/")
        payload = {
            "qr_token": qr_token,
            "otp_code": "333444",
            "source_account_number": self.customer_account.account_number,
        }
        resp = payer_client.post("/api/payments/qr/pay/", payload, format="json")
        _resp(resp, ["reference_number", "status"])
        self.assertEqual(resp.status_code, 201, f"6d: {resp.status_code} {resp.json()}")
        tx_ref = resp.json()["reference_number"]
        self.assertEqual(resp.json()["status"], "COMPLETED")
        print("  [PASS] 6d: QR payment executed -> 201, status=COMPLETED")

        # 6e: QR marked PAID
        from apps.payments.models import QRPayment
        qr = QRPayment.objects.get(qr_token=qr_token)
        self.assertEqual(qr.status, "PAID")
        print("  [PASS] 6e: QR status = PAID in DB")

        # 6f: Balances
        balance_after, _ = self._balance(account_id)
        merch_after, _ = self._balance(self.merchant_account.pk)
        self.assertEqual(balance_after, balance_before - Decimal("150.00"))
        self.assertEqual(merch_after, merch_before + Decimal("150.00"))
        print(f"  [PASS] 6f: Payer debited 150, merchant credited 150")

        # 6g: Double-entry
        balanced, debit, credit = self._entries_balanced(tx_ref)
        self.assertTrue(balanced)
        print(f"  [PASS] 6g: Double-entry balanced (DEBIT={debit} == CREDIT={credit})")

        # 6h: Can't pay same QR twice
        from apps.security.services import create_otp
        _, otp2 = create_otp(
            phone=user.phone_number, request_type="QR_PAYMENT", purpose_ref=qr_token, user=user
        )
        resp2 = payer_client.post("/api/payments/qr/pay/", {**payload, "otp_code": otp2}, format="json")
        self.assertEqual(resp2.status_code, 409, f"6h: expected 409, got {resp2.status_code}")
        print("  [PASS] 6h: Double-pay rejected -> 409")

    # ------------------------------------------------------------------
    # Scenario 7 — Bill Payment
    # ------------------------------------------------------------------

    def _scenario_bill_payment(self, access_token, account_id):
        print("\n--- STEP 7: Bill Payment Flow ---")
        client = self._bearer(access_token)

        balance_before, _ = self._balance(account_id)
        provider_before, _ = self._balance(self.provider_account.pk)
        service_number = "123456789001"

        # 7a: List providers
        _req("GET", "/api/payments/bill/providers/")
        resp = client.get("/api/payments/bill/providers/")
        _resp(resp)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)
        print("  [PASS] 7a: Provider list -> 200")

        # 7b: Fetch bill
        _req("POST", "/api/payments/bill/fetch/")
        resp = client.post(
            "/api/payments/bill/fetch/",
            {"provider_code": "ELEC-USD", "service_number": service_number},
            format="json",
        )
        _resp(resp, ["amount", "bill_reference"])
        self.assertEqual(resp.status_code, 200)
        bill_amount = Decimal(resp.json()["amount"])
        bill_ref = resp.json()["bill_reference"]
        self.assertGreater(bill_amount, Decimal("0"))
        print(f"  [PASS] 7b: Bill fetched -> amount={bill_amount}, ref={bill_ref}")

        # 7c: Request OTP
        _req("POST", "/api/payments/bill/otp/")
        resp = client.post(
            "/api/payments/bill/otp/",
            {"provider_code": "ELEC-USD", "service_number": service_number},
            format="json",
        )
        _resp(resp, ["detail"])
        self.assertEqual(resp.status_code, 200)
        print("  [PASS] 7c: Bill OTP sent -> 200")

        from apps.users.models import User
        user = User.objects.get(accounts__pk=account_id)
        purpose_ref = f"ELEC-USD:{service_number}"
        self._patch_otp(user.phone_number, "BILL_PAYMENT", purpose_ref, "555666")

        # 7d: Execute payment
        _req("POST", "/api/payments/bill/pay/")
        payload = {
            "provider_code": "ELEC-USD",
            "service_number": service_number,
            "bill_reference": bill_ref,
            "amount": str(bill_amount),
            "otp_code": "555666",
            "source_account_number": self.customer_account.account_number,
        }
        resp = client.post("/api/payments/bill/pay/", payload, format="json")
        _resp(resp, ["reference_number", "status"])
        self.assertEqual(resp.status_code, 201, f"7d: {resp.status_code} {resp.json()}")
        tx_ref = resp.json()["reference_number"]
        self.assertEqual(resp.json()["status"], "COMPLETED")
        print("  [PASS] 7d: Bill payment executed -> 201, status=COMPLETED")

        # 7e: BillPayment record
        from apps.payments.models import BillPayment
        from apps.ledger.models import Transaction
        tx = Transaction.objects.get(reference_number=tx_ref)
        bp = BillPayment.objects.filter(transaction=tx).first()
        self.assertIsNotNone(bp)
        self.assertEqual(bp.service_number, service_number)
        print("  [PASS] 7e: BillPayment record created with correct service_number")

        # 7f: Balances
        balance_after, _ = self._balance(account_id)
        provider_after, _ = self._balance(self.provider_account.pk)
        self.assertEqual(balance_after, balance_before - bill_amount)
        self.assertEqual(provider_after, provider_before + bill_amount)
        print(f"  [PASS] 7f: Payer debited {bill_amount}, provider credited {bill_amount}")

        # 7g: No negative balance
        self.assertGreaterEqual(balance_after, Decimal("0"))
        print("  [PASS] 7g: No negative balance")

        # 7h: Double-entry
        balanced, debit, credit = self._entries_balanced(tx_ref)
        self.assertTrue(balanced)
        print(f"  [PASS] 7h: Double-entry balanced (DEBIT={debit} == CREDIT={credit})")

        # 7i: OTP not reusable
        _req("POST", "/api/payments/bill/pay/ [replay OTP]")
        resp2 = client.post("/api/payments/bill/pay/", payload, format="json")
        self.assertEqual(resp2.status_code, 400, f"7i: expected 400, got {resp2.status_code}")
        print(f"  [PASS] 7i: Bill OTP not reusable -> {resp2.status_code}")
