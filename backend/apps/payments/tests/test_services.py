"""
Tests for payments services:
  - create_transfer
  - generate_qr_code / process_qr_payment
  - fetch_bill_info / process_bill_payment
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.constants import AccountStatus
from apps.accounts.models import Account, Currency
from apps.ledger.constants import TransactionStatus
from apps.users.constants import UserStatus
from apps.users.models import User

from ..constants import QRAmountMode, QRPaymentStatus
from ..exceptions import (
    BillProviderNotFoundError,
    MerchantNotFoundError,
    QRTokenAlreadyPaidError,
    QRTokenExpiredError,
    QRTokenNotFoundError,
    TransferSameAccountError,
)
from ..models import BillPayment, BillProvider, MerchantProfile, QRPayment
from ..services import (
    create_transfer,
    fetch_bill_info,
    generate_qr_code,
    process_bill_payment,
    process_qr_payment,
)


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


def _account(owner: User, balance: Decimal = Decimal("1000.00"), status: str = AccountStatus.ACTIVE):
    currency = _currency()
    acc = Account.objects.create(
        user=owner,
        currency=currency,
        account_number=f"{2000 + Account.objects.count():016d}",
        account_name=f"Account {owner.phone_number}",
        status=status,
        available_balance=balance,
        ledger_balance=balance,
    )
    return acc


def _merchant(user: User, account: Account):
    return MerchantProfile.objects.create(
        user=user,
        settlement_account=account,
        business_name="Test Shop",
        business_type="Retail",
        registration_number=f"REG{user.pk:06d}",
        contact_phone=user.phone_number,
    )


def _bill_provider(account: Account, code: str = "ELEC-001"):
    return BillProvider.objects.create(
        code=code,
        name="National Electricity",
        service_type="ELECTRICITY",
        provider_account=account,
    )


# ---------------------------------------------------------------------------
# Transfer tests
# ---------------------------------------------------------------------------

class CreateTransferTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.sender = _user("+966500001001")
        self.receiver = _user("+966500001002")
        self.source = _account(self.sender, Decimal("500.00"))
        self.dest = _account(self.receiver, Decimal("0.00"))

    def test_transfer_succeeds(self):
        tx = create_transfer(
            customer=self.sender,
            source_account=self.source,
            destination_account=self.dest,
            amount=Decimal("100.00"),
            currency_code="USD",
        )
        self.assertEqual(tx.status, TransactionStatus.COMPLETED)

    def test_source_debited(self):
        create_transfer(
            customer=self.sender,
            source_account=self.source,
            destination_account=self.dest,
            amount=Decimal("200.00"),
            currency_code="USD",
        )
        self.source.refresh_from_db()
        self.assertEqual(self.source.available_balance, Decimal("300.00"))

    def test_dest_credited(self):
        create_transfer(
            customer=self.sender,
            source_account=self.source,
            destination_account=self.dest,
            amount=Decimal("150.00"),
            currency_code="USD",
        )
        self.dest.refresh_from_db()
        self.assertEqual(self.dest.available_balance, Decimal("150.00"))

    def test_same_account_raises(self):
        with self.assertRaises(TransferSameAccountError):
            create_transfer(
                customer=self.sender,
                source_account=self.source,
                destination_account=self.source,
                amount=Decimal("50.00"),
                currency_code="USD",
            )

    def test_insufficient_funds_raises(self):
        from apps.accounts.exceptions import InsufficientFundsError
        with self.assertRaises(InsufficientFundsError):
            create_transfer(
                customer=self.sender,
                source_account=self.source,
                destination_account=self.dest,
                amount=Decimal("9999.00"),
                currency_code="USD",
            )


# ---------------------------------------------------------------------------
# QR Payment tests
# ---------------------------------------------------------------------------

class GenerateQRCodeTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.merchant_user = _user("+966500001010")
        self.merchant_account = _account(self.merchant_user, Decimal("0.00"))
        self.profile = _merchant(self.merchant_user, self.merchant_account)

    def test_generate_fixed_qr(self):
        qr = generate_qr_code(
            merchant=self.merchant_user,
            amount=Decimal("50.00"),
        )
        self.assertEqual(qr.amount_mode, QRAmountMode.FIXED)
        self.assertEqual(qr.display_amount, Decimal("50.00"))
        self.assertEqual(qr.status, QRPaymentStatus.PENDING)
        self.assertIsNotNone(qr.qr_token)

    def test_generate_open_qr(self):
        qr = generate_qr_code(merchant=self.merchant_user)
        self.assertEqual(qr.amount_mode, QRAmountMode.OPEN)
        self.assertIsNone(qr.display_amount)

    def test_no_profile_raises(self):
        other = _user("+966500001011")
        with self.assertRaises(MerchantNotFoundError):
            generate_qr_code(merchant=other, amount=Decimal("10.00"))


class ProcessQRPaymentTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.merchant_user = _user("+966500001020")
        self.merchant_account = _account(self.merchant_user, Decimal("0.00"))
        self.profile = _merchant(self.merchant_user, self.merchant_account)

        self.payer = _user("+966500001021")
        self.payer_account = _account(self.payer, Decimal("500.00"))

        self.qr = generate_qr_code(
            merchant=self.merchant_user,
            amount=Decimal("75.00"),
        )

    def _otp(self):
        return _issue_and_get_otp(self.payer, OTPRequestType.QR_PAYMENT, self.qr.qr_token)

    def test_qr_payment_succeeds(self):
        otp = self._otp()
        tx = process_qr_payment(
            payer=self.payer,
            payer_account=self.payer_account,
            qr_token=self.qr.qr_token,
            otp_code=otp,
        )
        self.assertEqual(tx.status, TransactionStatus.COMPLETED)

    def test_merchant_account_credited(self):
        otp = self._otp()
        process_qr_payment(
            payer=self.payer,
            payer_account=self.payer_account,
            qr_token=self.qr.qr_token,
            otp_code=otp,
        )
        self.merchant_account.refresh_from_db()
        self.assertEqual(self.merchant_account.available_balance, Decimal("75.00"))

    def test_qr_marked_paid(self):
        otp = self._otp()
        process_qr_payment(
            payer=self.payer,
            payer_account=self.payer_account,
            qr_token=self.qr.qr_token,
            otp_code=otp,
        )
        self.qr.refresh_from_db()
        self.assertEqual(self.qr.status, QRPaymentStatus.PAID)

    def test_double_payment_raises(self):
        from apps.security.services import create_otp
        otp1 = self._otp()
        process_qr_payment(
            payer=self.payer,
            payer_account=self.payer_account,
            qr_token=self.qr.qr_token,
            otp_code=otp1,
        )
        # Try to pay again
        _, otp2 = create_otp(
            phone=self.payer.phone_number,
            request_type=OTPRequestType.QR_PAYMENT,
            purpose_ref=self.qr.qr_token,
            user=self.payer,
        )
        with self.assertRaises(QRTokenAlreadyPaidError):
            process_qr_payment(
                payer=self.payer,
                payer_account=self.payer_account,
                qr_token=self.qr.qr_token,
                otp_code=otp2,
            )

    def test_expired_qr_raises(self):
        # Force-expire the QR
        QRPayment.objects.filter(pk=self.qr.pk).update(
            expires_at=timezone.now() - timezone.timedelta(hours=1)
        )
        otp = self._otp()
        with self.assertRaises(QRTokenExpiredError):
            process_qr_payment(
                payer=self.payer,
                payer_account=self.payer_account,
                qr_token=self.qr.qr_token,
                otp_code=otp,
            )

    def test_invalid_token_raises(self):
        otp = self._otp()
        with self.assertRaises(QRTokenNotFoundError):
            process_qr_payment(
                payer=self.payer,
                payer_account=self.payer_account,
                qr_token="NONEXISTENT_TOKEN",
                otp_code=otp,
            )


# ---------------------------------------------------------------------------
# Bill Payment tests
# ---------------------------------------------------------------------------

class FetchBillInfoTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.provider_user = _user("+966500001030")
        self.provider_account = _account(self.provider_user, Decimal("0.00"))
        self.provider = _bill_provider(self.provider_account)

    def test_fetch_returns_bill_info(self):
        info = fetch_bill_info(
            provider_code="ELEC-001",
            service_number="123456789012",
        )
        self.assertEqual(info["provider_code"], "ELEC-001")
        self.assertIn("amount", info)
        self.assertIn("bill_reference", info)

    def test_unknown_provider_raises(self):
        with self.assertRaises(BillProviderNotFoundError):
            fetch_bill_info(provider_code="UNKNOWN", service_number="123")


class ProcessBillPaymentTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.provider_user = _user("+966500001040")
        self.provider_account = _account(self.provider_user, Decimal("0.00"))
        self.provider = _bill_provider(self.provider_account)

        self.customer = _user("+966500001041")
        self.payer_account = _account(self.customer, Decimal("500.00"))

    def _otp(self, service_number="123456789012"):
        purpose_ref = f"ELEC-001:{service_number}"
        return _issue_and_get_otp(self.customer, OTPRequestType.BILL_PAYMENT, purpose_ref)

    def test_bill_payment_succeeds(self):
        otp = self._otp()
        tx = process_bill_payment(
            customer=self.customer,
            payer_account=self.payer_account,
            provider_code="ELEC-001",
            service_number="123456789012",
            bill_reference="BILL-ELEC-001-789012",
            amount=Decimal("150.00"),
            otp_code=otp,
        )
        self.assertEqual(tx.status, TransactionStatus.COMPLETED)

    def test_provider_account_credited(self):
        otp = self._otp()
        process_bill_payment(
            customer=self.customer,
            payer_account=self.payer_account,
            provider_code="ELEC-001",
            service_number="123456789012",
            bill_reference="BILL-ELEC-001-789012",
            amount=Decimal("100.00"),
            otp_code=otp,
        )
        self.provider_account.refresh_from_db()
        self.assertEqual(self.provider_account.available_balance, Decimal("100.00"))

    def test_bill_payment_record_created(self):
        otp = self._otp()
        tx = process_bill_payment(
            customer=self.customer,
            payer_account=self.payer_account,
            provider_code="ELEC-001",
            service_number="123456789012",
            bill_reference="BILL-ELEC-001-789012",
            amount=Decimal("80.00"),
            otp_code=otp,
        )
        self.assertTrue(BillPayment.objects.filter(transaction=tx).exists())

    def test_unknown_provider_raises(self):
        otp = _issue_and_get_otp(
            self.customer,
            OTPRequestType.BILL_PAYMENT,
            "BADPROVIDER:123",
        )
        with self.assertRaises(BillProviderNotFoundError):
            process_bill_payment(
                customer=self.customer,
                payer_account=self.payer_account,
                provider_code="BADPROVIDER",
                service_number="123",
                bill_reference="X",
                amount=Decimal("50.00"),
                otp_code=otp,
            )

    def test_wrong_otp_raises(self):
        from apps.security.exceptions import OTPInvalidError
        _issue_and_get_otp(self.customer, OTPRequestType.BILL_PAYMENT, "ELEC-001:123456789012")
        with self.assertRaises(OTPInvalidError):
            process_bill_payment(
                customer=self.customer,
                payer_account=self.payer_account,
                provider_code="ELEC-001",
                service_number="123456789012",
                bill_reference="REF",
                amount=Decimal("50.00"),
                otp_code="000000",
            )
