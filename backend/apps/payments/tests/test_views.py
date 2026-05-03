"""Integration tests for payments API views."""
from decimal import Decimal

from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth.hashers import make_password
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.constants import AccountStatus
from apps.accounts.models import Account, Currency
from apps.users.constants import UserStatus
from apps.users.models import User

from ..models import BillProvider, MerchantProfile, QRPayment
from ..services import generate_qr_code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _currency():
    return Currency.objects.get_or_create(
        code="USD",
        defaults={"name": "US Dollar", "symbol": "﷼", "decimal_places": 2},
    )[0]


def _user(phone: str, status: str = UserStatus.ACTIVE):
    from apps.users.constants import KycStatus
    return User.objects.create_user(
        phone_number=phone,
        password="TestPass1!",
        status=status,
        kyc_status=KycStatus.APPROVED,
    )


def _account(owner: User, balance: Decimal = Decimal("1000.00")):
    _currency()
    acc = Account.objects.create(
        user=owner,
        currency=Currency.objects.get(code="USD"),
        account_number=f"{5000 + Account.objects.count():016d}",
        account_name=f"Account {owner.phone_number}",
        status=AccountStatus.ACTIVE,
        available_balance=balance,
        ledger_balance=balance,
    )
    return acc


def _auth_client(user: User) -> APIClient:
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def _merchant(user: User, account: Account):
    return MerchantProfile.objects.create(
        user=user,
        settlement_account=account,
        business_name="Test Shop",
        business_type="Retail",
        registration_number=f"REG{user.pk:06d}",
        contact_phone=user.phone_number,
    )


def _bill_provider(account: Account, code: str = "WATER-001"):
    return BillProvider.objects.create(
        code=code,
        name="Water Corp",
        service_type="WATER",
        provider_account=account,
    )


# ---------------------------------------------------------------------------
# Transfer view tests
# ---------------------------------------------------------------------------

class TransferOTPViewTest(TestCase):
    def setUp(self):
        _currency()
        self.user = _user("+966500002001")
        self.client = _auth_client(self.user)

    @override_settings(DEBUG=True)
    def test_otp_sent_includes_dev_otp_when_debug_true(self):
        response = self.client.post("/api/payments/transfer/otp/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("dev_otp", response.data)

    @override_settings(DEBUG=False, ENABLE_DEV_OTP=False)
    def test_otp_sent_does_not_include_dev_otp_when_debug_false(self):
        response = self.client.post("/api/payments/transfer/otp/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("dev_otp", response.data)
        self.assertNotIn("_debug_otp", response.data)

    def test_unauthenticated_denied(self):
        response = APIClient().post("/api/payments/transfer/otp/")
        self.assertEqual(response.status_code, 401)


class TransferExecuteViewTest(TestCase):
    def setUp(self):
        _currency()
        self.sender = _user("+966500002010")
        self.receiver = _user("+966500002011")
        self.sender.pin_hash = make_password("1234")
        self.sender.save(update_fields=["pin_hash"])
        self.source = _account(self.sender, Decimal("500.00"))
        self.dest = _account(self.receiver, Decimal("0.00"))
        self.client = _auth_client(self.sender)

    def test_transfer_succeeds(self):
        payload = {
            "destination_account_number": self.dest.account_number,
            "amount": "100.00",
            "pin": "1234",
        }
        response = self.client.post("/api/payments/transfer/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("reference_number", response.data)

    def test_transfer_succeeds_with_destination_phone_number(self):
        payload = {
            "destination_phone_number": self.receiver.phone_number,
            "amount": "100.00",
            "pin": "1234",
        }
        response = self.client.post("/api/payments/transfer/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("reference_number", response.data)

    def test_transfer_unknown_destination_phone_returns_404(self):
        payload = {
            "destination_phone_number": "+966599999999",
            "amount": "10.00",
            "pin": "1234",
        }
        response = self.client.post("/api/payments/transfer/", payload, format="json")
        self.assertEqual(response.status_code, 404)

    def test_invalid_destination_account_returns_400_not_500(self):
        payload = {
            "destination_account_number": "+252771000011",
            "amount": "10.00",
            "pin": "1234",
        }
        response = self.client.post("/api/payments/transfer/", payload, format="json")
        self.assertEqual(response.status_code, 400, response.data)

    def test_wrong_pin_returns_401(self):
        payload = {
            "destination_account_number": self.dest.account_number,
            "amount": "100.00",
            "pin": "9999",
        }
        response = self.client.post("/api/payments/transfer/", payload, format="json")
        self.assertEqual(response.status_code, 401)

    def test_insufficient_funds_returns_422(self):
        payload = {
            "destination_account_number": self.dest.account_number,
            "amount": "9999.00",
            "pin": "1234",
        }
        response = self.client.post("/api/payments/transfer/", payload, format="json")
        self.assertEqual(response.status_code, 422)

    def test_unknown_dest_returns_404(self):
        payload = {
            "destination_account_number": "0000000000000000",
            "amount": "50.00",
            "pin": "1234",
        }
        response = self.client.post("/api/payments/transfer/", payload, format="json")
        self.assertEqual(response.status_code, 404)

    def test_pending_user_denied(self):
        pending = _user("+966500002012", status=UserStatus.PENDING_VERIFICATION)
        client = _auth_client(pending)
        response = client.post("/api/payments/transfer/otp/")
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# QR Payment view tests
# ---------------------------------------------------------------------------

class QRGenerateViewTest(TestCase):
    def setUp(self):
        _currency()
        self.merchant_user = _user("+966500002020")
        self.merchant_account = _account(self.merchant_user, Decimal("0.00"))
        self.profile = _merchant(self.merchant_user, self.merchant_account)
        self.client = _auth_client(self.merchant_user)

    def test_generate_fixed_qr(self):
        response = self.client.post(
            "/api/merchant/qr/generate/",
            {"amount": "50.00", "currency_code": "USD"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("qr_token", response.data)

    def test_generate_open_qr(self):
        response = self.client.post(
            "/api/merchant/qr/generate/",
            {"currency_code": "USD"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["amount_mode"], "OPEN")

    def test_non_merchant_returns_403(self):
        other = _user("+966500002021")
        client = _auth_client(other)
        response = client.post(
            "/api/merchant/qr/generate/",
            {"amount": "10.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class QRResolveViewTest(TestCase):
    def setUp(self):
        _currency()
        self.merchant_user = _user("+966500002030")
        self.merchant_account = _account(self.merchant_user)
        self.profile = _merchant(self.merchant_user, self.merchant_account)
        self.qr = generate_qr_code(merchant=self.merchant_user, amount=Decimal("25.00"))
        self.payer = _user("+966500002031")
        self.client = _auth_client(self.payer)

    def test_resolve_returns_qr_details(self):
        response = self.client.get(f"/api/payments/qr/{self.qr.qr_token}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["qr_token"], self.qr.qr_token)

    def test_unknown_token_returns_404(self):
        response = self.client.get("/api/payments/qr/NONEXISTENT/")
        self.assertEqual(response.status_code, 404)


class QRPayExecuteViewTest(TestCase):
    def setUp(self):
        _currency()
        self.merchant_user = _user("+966500002040")
        self.merchant_account = _account(self.merchant_user, Decimal("0.00"))
        self.profile = _merchant(self.merchant_user, self.merchant_account)
        self.qr = generate_qr_code(merchant=self.merchant_user, amount=Decimal("60.00"))

        self.payer = _user("+966500002041")
        self.payer_account = _account(self.payer, Decimal("500.00"))
        self.client = _auth_client(self.payer)

    def test_qr_payment_succeeds(self):
        otp = _otp(self.payer, OTPRequestType.QR_PAYMENT, self.qr.qr_token)
        payload = {
            "qr_token": self.qr.qr_token,
            "otp_code": otp,
            "source_account_number": self.payer_account.account_number,
        }
        response = self.client.post("/api/payments/qr/pay/", payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_wrong_otp_returns_400(self):
        _otp(self.payer, OTPRequestType.QR_PAYMENT, self.qr.qr_token)
        payload = {
            "qr_token": self.qr.qr_token,
            "otp_code": "000000",
            "source_account_number": self.payer_account.account_number,
        }
        response = self.client.post("/api/payments/qr/pay/", payload, format="json")
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# Bill Payment view tests
# ---------------------------------------------------------------------------

class BillProviderListViewTest(TestCase):
    def setUp(self):
        _currency()
        self.user = _user("+966500002050")
        self.provider_account = _account(self.user, Decimal("0.00"))
        _bill_provider(self.provider_account)
        self.client = _auth_client(self.user)

    def test_list_providers(self):
        response = self.client.get("/api/payments/bill/providers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class BillFetchViewTest(TestCase):
    def setUp(self):
        _currency()
        self.user = _user("+966500002060")
        self.provider_account = _account(self.user, Decimal("0.00"))
        _bill_provider(self.provider_account, code="WATER-001")
        self.client = _auth_client(self.user)

    def test_fetch_bill(self):
        response = self.client.post(
            "/api/payments/bill/fetch/",
            {"provider_code": "WATER-001", "service_number": "999999999999"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("amount", response.data)

    def test_unknown_provider_returns_404(self):
        response = self.client.post(
            "/api/payments/bill/fetch/",
            {"provider_code": "UNKNOWN", "service_number": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)


class BillPayExecuteViewTest(TestCase):
    def setUp(self):
        _currency()
        self.provider_owner = _user("+966500002070")
        self.provider_account = _account(self.provider_owner, Decimal("0.00"))
        self.provider = _bill_provider(self.provider_account, code="WATER-001")

        self.customer = _user("+966500002071")
        self.payer_account = _account(self.customer, Decimal("500.00"))
        self.client = _auth_client(self.customer)

    def test_bill_payment_succeeds(self):
        service_number = "123456789012"
        otp = _otp(self.customer, OTPRequestType.BILL_PAYMENT, f"WATER-001:{service_number}")
        payload = {
            "provider_code": "WATER-001",
            "service_number": service_number,
            "bill_reference": "BILL-WATER-001-789012",
            "amount": "100.00",
            "otp_code": otp,
            "source_account_number": self.payer_account.account_number,
        }
        response = self.client.post("/api/payments/bill/pay/", payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_wrong_otp_returns_400(self):
        service_number = "123456789099"
        _otp(self.customer, OTPRequestType.BILL_PAYMENT, f"WATER-001:{service_number}")
        payload = {
            "provider_code": "WATER-001",
            "service_number": service_number,
            "bill_reference": "REF",
            "amount": "50.00",
            "otp_code": "000000",
            "source_account_number": self.payer_account.account_number,
        }
        response = self.client.post("/api/payments/bill/pay/", payload, format="json")
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# Merchant view tests
# ---------------------------------------------------------------------------

class MerchantProfileViewTest(TestCase):
    def setUp(self):
        _currency()
        self.merchant_user = _user("+966500002080")
        self.merchant_account = _account(self.merchant_user)
        self.profile = _merchant(self.merchant_user, self.merchant_account)
        self.client = _auth_client(self.merchant_user)

    def test_profile_returned(self):
        response = self.client.get("/api/merchant/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["business_name"], "Test Shop")

    def test_no_profile_returns_404(self):
        other = _user("+966500002081")
        client = _auth_client(other)
        response = client.get("/api/merchant/profile/")
        self.assertEqual(response.status_code, 404)
