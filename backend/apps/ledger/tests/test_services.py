"""
Tests for ledger services:
  - post_transaction
  - calculate_fee
  - reverse_transaction
  - archive_transaction
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.constants import AccountStatus
from apps.accounts.models import Account, Currency
from apps.users.constants import UserStatus
from apps.users.models import User

from ..constants import EntryType, TransactionStatus, TransactionType
from ..exceptions import (
    DuplicateTransactionError,
    TransactionAlreadyReversedError,
    TransactionBalanceError,
    TransactionNotFoundError,
    TransactionNotReversibleError,
    UserNotActiveError,
)
from ..models import FeeRule, Transaction, TransactionEntry
from ..services import (
    archive_transaction,
    calculate_fee,
    post_transaction,
    reverse_transaction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _currency() -> Currency:
    return Currency.objects.get_or_create(
        code="USD",
        defaults={"name": "US Dollar", "symbol": "﷼", "decimal_places": 2},
    )[0]


def _user(phone: str = "+966500000001", status: str = UserStatus.ACTIVE) -> User:
    from apps.users.constants import KycStatus
    u = User.objects.create_user(
        phone_number=phone,
        password="TestPass1!",
        status=status,
        kyc_status=KycStatus.APPROVED,
    )
    return u


def _account(
    owner: User,
    balance: Decimal = Decimal("1000.00"),
    account_status: str = AccountStatus.ACTIVE,
    currency: Currency | None = None,
) -> Account:
    if currency is None:
        currency = _currency()
    acc = Account.objects.create(
        user=owner,
        currency=currency,
        account_number=f"{1000 + Account.objects.count():016d}",
        account_name=f"{owner.phone_number} Account",
        status=account_status,
        available_balance=balance,
        ledger_balance=balance,
    )
    return acc


# ---------------------------------------------------------------------------
# post_transaction tests
# ---------------------------------------------------------------------------

class PostTransactionBasicTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.sender = _user("+966500000001")
        self.receiver = _user("+966500000002")
        self.source = _account(self.sender, Decimal("500.00"))
        self.dest = _account(self.receiver, Decimal("100.00"))

    def test_transfer_creates_completed_transaction(self):
        tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("200.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.sender,
            initiated_by=self.sender,
        )
        self.assertEqual(tx.status, TransactionStatus.COMPLETED)
        self.assertEqual(tx.transaction_type, TransactionType.TRANSFER)
        self.assertIsNotNone(tx.completed_at)
        self.assertTrue(tx.reference_number.startswith("TRF"))

    def test_source_balance_decremented(self):
        post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("200.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.sender,
        )
        self.source.refresh_from_db()
        self.assertEqual(self.source.available_balance, Decimal("300.00"))
        self.assertEqual(self.source.ledger_balance, Decimal("300.00"))

    def test_destination_balance_incremented(self):
        post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("200.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.sender,
        )
        self.dest.refresh_from_db()
        self.assertEqual(self.dest.available_balance, Decimal("300.00"))

    def test_double_entry_created(self):
        tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("150.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.sender,
        )
        entries = list(tx.entries.order_by("sequence_no"))
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].entry_type, EntryType.DEBIT)
        self.assertEqual(entries[0].account_id, self.source.pk)
        self.assertEqual(entries[1].entry_type, EntryType.CREDIT)
        self.assertEqual(entries[1].account_id, self.dest.pk)

    def test_double_entry_balances(self):
        tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("150.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.sender,
        )
        debit_total = sum(
            e.amount for e in tx.entries.all() if e.entry_type in EntryType.DEBIT_TYPES
        )
        credit_total = sum(
            e.amount for e in tx.entries.all() if e.entry_type in EntryType.CREDIT_TYPES
        )
        self.assertEqual(debit_total, credit_total)


class PostTransactionGuardTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.sender = _user("+966500000003")
        self.receiver = _user("+966500000004")
        self.source = _account(self.sender, Decimal("500.00"))
        self.dest = _account(self.receiver, Decimal("0.00"))

    def test_insufficient_funds_raises(self):
        from apps.accounts.exceptions import InsufficientFundsError
        with self.assertRaises(InsufficientFundsError):
            post_transaction(
                transaction_type=TransactionType.TRANSFER,
                currency_code="USD",
                amount=Decimal("9999.00"),
                source_account=self.source,
                destination_account=self.dest,
                customer=self.sender,
            )

    def test_frozen_source_raises(self):
        from apps.accounts.exceptions import AccountRestrictedError
        Account.objects.filter(pk=self.source.pk).update(status=AccountStatus.FROZEN)
        self.source.refresh_from_db()
        with self.assertRaises(AccountRestrictedError):
            post_transaction(
                transaction_type=TransactionType.TRANSFER,
                currency_code="USD",
                amount=Decimal("100.00"),
                source_account=self.source,
                destination_account=self.dest,
                customer=self.sender,
            )

    def test_pending_user_raises(self):
        pending_user = _user("+966500000005", status=UserStatus.PENDING_VERIFICATION)
        with self.assertRaises(UserNotActiveError):
            post_transaction(
                transaction_type=TransactionType.TRANSFER,
                currency_code="USD",
                amount=Decimal("100.00"),
                source_account=self.source,
                destination_account=self.dest,
                customer=pending_user,
            )

    def test_same_account_raises(self):
        with self.assertRaises(ValueError):
            post_transaction(
                transaction_type=TransactionType.TRANSFER,
                currency_code="USD",
                amount=Decimal("100.00"),
                source_account=self.source,
                destination_account=self.source,
                customer=self.sender,
            )

    def test_negative_amount_raises(self):
        with self.assertRaises(ValueError):
            post_transaction(
                transaction_type=TransactionType.TRANSFER,
                currency_code="USD",
                amount=Decimal("-50.00"),
                source_account=self.source,
                destination_account=self.dest,
                customer=self.sender,
            )

    def test_blocked_source_raises(self):
        from apps.accounts.exceptions import AccountRestrictedError
        Account.objects.filter(pk=self.source.pk).update(status=AccountStatus.BLOCKED)
        self.source.refresh_from_db()
        with self.assertRaises(AccountRestrictedError):
            post_transaction(
                transaction_type=TransactionType.TRANSFER,
                currency_code="USD",
                amount=Decimal("100.00"),
                source_account=self.source,
                destination_account=self.dest,
                customer=self.sender,
            )


class PostTransactionIdempotencyTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.sender = _user("+966500000006")
        self.receiver = _user("+966500000007")
        self.source = _account(self.sender, Decimal("1000.00"))
        self.dest = _account(self.receiver, Decimal("0.00"))

    def test_idempotency_key_returns_existing_completed(self):
        key = "idem-test-001"
        tx1 = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("100.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.sender,
            idempotency_key=key,
        )
        # Balance should only move once
        self.source.refresh_from_db()
        balance_after_first = self.source.available_balance

        tx2 = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("100.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.sender,
            idempotency_key=key,
        )

        self.assertEqual(tx1.pk, tx2.pk)
        self.source.refresh_from_db()
        self.assertEqual(self.source.available_balance, balance_after_first)


# ---------------------------------------------------------------------------
# Fee calculation tests
# ---------------------------------------------------------------------------

class CalculateFeeTest(TestCase):
    def setUp(self):
        self.currency = _currency()

    def test_no_rule_returns_zero(self):
        fee, pool = calculate_fee(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("500.00"),
        )
        self.assertEqual(fee, Decimal("0"))
        self.assertIsNone(pool)

    def test_flat_fee_rule(self):
        FeeRule.objects.create(
            name="Flat 5 USD",
            transaction_type=TransactionType.TRANSFER,
            currency=self.currency,
            fixed_fee=Decimal("5.00"),
            percentage_fee=Decimal("0"),
            min_fee=Decimal("0"),
            effective_from=timezone.now(),
        )
        # No pool account configured — fee returns 0 when pool missing
        fee, pool = calculate_fee(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("500.00"),
        )
        # LEDGER_FEE_POOL_ACCOUNT_NUMBER is "" in test settings → fee is 0
        self.assertEqual(fee, Decimal("0"))
        self.assertIsNone(pool)

    def test_fee_with_pool_account(self):
        """When a fee pool account is set up, fees are charged."""
        from django.conf import settings as django_settings

        # Create a pool account owned by the sender (any active account)
        owner = _user("+966500000099")
        pool_acc = _account(owner, Decimal("0.00"))
        original_setting = getattr(django_settings, "LEDGER_FEE_POOL_ACCOUNT_NUMBER", "")
        django_settings.LEDGER_FEE_POOL_ACCOUNT_NUMBER = pool_acc.account_number

        FeeRule.objects.create(
            name="1% TRANSFER fee",
            transaction_type=TransactionType.TRANSFER,
            currency=self.currency,
            fixed_fee=Decimal("0"),
            percentage_fee=Decimal("0.0100"),  # 1%
            min_fee=Decimal("1.00"),
            effective_from=timezone.now(),
        )
        try:
            fee, pool = calculate_fee(
                transaction_type=TransactionType.TRANSFER,
                currency_code="USD",
                amount=Decimal("500.00"),
            )
            self.assertEqual(fee, Decimal("5.00"))  # 500 × 1% = 5
            self.assertEqual(pool.pk, pool_acc.pk)
        finally:
            django_settings.LEDGER_FEE_POOL_ACCOUNT_NUMBER = original_setting

    def test_percentage_fee_with_max_cap(self):
        """Max fee cap is respected."""
        from django.conf import settings as django_settings

        owner = _user("+966500000098")
        pool_acc = _account(owner, Decimal("0.00"))
        original_setting = getattr(django_settings, "LEDGER_FEE_POOL_ACCOUNT_NUMBER", "")
        django_settings.LEDGER_FEE_POOL_ACCOUNT_NUMBER = pool_acc.account_number

        FeeRule.objects.create(
            name="1% capped at 10",
            transaction_type=TransactionType.TRANSFER,
            currency=self.currency,
            fixed_fee=Decimal("0"),
            percentage_fee=Decimal("0.0100"),
            min_fee=Decimal("0"),
            max_fee=Decimal("10.00"),
            effective_from=timezone.now(),
        )
        try:
            fee, _ = calculate_fee(
                transaction_type=TransactionType.TRANSFER,
                currency_code="USD",
                amount=Decimal("5000.00"),  # Would be 50 without cap
            )
            self.assertEqual(fee, Decimal("10.00"))
        finally:
            django_settings.LEDGER_FEE_POOL_ACCOUNT_NUMBER = original_setting


# ---------------------------------------------------------------------------
# reverse_transaction tests
# ---------------------------------------------------------------------------

class ReverseTransactionTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.sender = _user("+966500000010")
        self.receiver = _user("+966500000011")
        self.source = _account(self.sender, Decimal("1000.00"))
        self.dest = _account(self.receiver, Decimal("0.00"))
        self.tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("300.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.sender,
        )

    def test_reversal_creates_new_transaction(self):
        reversal = reverse_transaction(
            reference_number=self.tx.reference_number,
            reason="Customer requested cancellation",
        )
        self.assertEqual(reversal.status, TransactionStatus.COMPLETED)
        self.assertEqual(reversal.parent_transaction_id, self.tx.pk)
        self.assertNotEqual(reversal.reference_number, self.tx.reference_number)

    def test_original_marked_reversed(self):
        reverse_transaction(
            reference_number=self.tx.reference_number,
            reason="Test reversal",
        )
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, TransactionStatus.REVERSED)
        self.assertIsNotNone(self.tx.reversed_at)

    def test_balances_restored_after_reversal(self):
        reverse_transaction(
            reference_number=self.tx.reference_number,
            reason="Balance restore test",
        )
        self.source.refresh_from_db()
        self.dest.refresh_from_db()
        self.assertEqual(self.source.available_balance, Decimal("1000.00"))
        self.assertEqual(self.dest.available_balance, Decimal("0.00"))

    def test_reversal_entries_are_balanced(self):
        reversal = reverse_transaction(
            reference_number=self.tx.reference_number,
            reason="Balance check",
        )
        debit_total = sum(
            e.amount for e in reversal.entries.all() if e.entry_type in EntryType.DEBIT_TYPES
        )
        credit_total = sum(
            e.amount for e in reversal.entries.all() if e.entry_type in EntryType.CREDIT_TYPES
        )
        self.assertEqual(debit_total, credit_total)

    def test_cannot_reverse_twice(self):
        reverse_transaction(
            reference_number=self.tx.reference_number,
            reason="First reversal",
        )
        with self.assertRaises(TransactionAlreadyReversedError):
            reverse_transaction(
                reference_number=self.tx.reference_number,
                reason="Second reversal",
            )

    def test_cannot_reverse_non_completed(self):
        # Create a PROCESSING transaction manually
        tx = Transaction.objects.create(
            reference_number="TRF999FAKE",
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.PROCESSING,
            currency_id="USD",
            amount=Decimal("50.00"),
        )
        with self.assertRaises(TransactionNotReversibleError):
            reverse_transaction(
                reference_number="TRF999FAKE",
                reason="Should fail",
            )

    def test_not_found_raises(self):
        with self.assertRaises(TransactionNotFoundError):
            reverse_transaction(
                reference_number="TRFNONEXISTENT",
                reason="Should fail",
            )


# ---------------------------------------------------------------------------
# archive_transaction tests
# ---------------------------------------------------------------------------

class ArchiveTransactionTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.sender = _user("+966500000020")
        self.receiver = _user("+966500000021")
        self.source = _account(self.sender, Decimal("500.00"))
        self.dest = _account(self.receiver, Decimal("0.00"))
        self.tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("100.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.sender,
        )

    def test_archive_creates_history_record(self):
        history = archive_transaction(self.tx)
        self.assertEqual(history.reference_number, self.tx.reference_number)
        self.assertEqual(history.transaction_id, self.tx.pk)
        self.assertEqual(history.currency_code, "USD")

    def test_archive_is_idempotent(self):
        h1 = archive_transaction(self.tx)
        h2 = archive_transaction(self.tx)
        self.assertEqual(h1.pk, h2.pk)

    def test_archive_payload_contains_entries(self):
        history = archive_transaction(self.tx)
        self.assertIn("entries", history.payload_json)
        self.assertEqual(len(history.payload_json["entries"]), 2)


# ---------------------------------------------------------------------------
# pending-user guard integration
# ---------------------------------------------------------------------------

class PendingUserGuardTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.pending_user = _user("+966500000030", status=UserStatus.PENDING_VERIFICATION)
        self.active_user = _user("+966500000031")
        self.source = _account(self.pending_user, Decimal("1000.00"))
        self.dest = _account(self.active_user, Decimal("0.00"))

    def test_pending_customer_blocked(self):
        with self.assertRaises(UserNotActiveError):
            post_transaction(
                transaction_type=TransactionType.TRANSFER,
                currency_code="USD",
                amount=Decimal("100.00"),
                source_account=self.source,
                destination_account=self.dest,
                customer=self.pending_user,
            )

    def test_active_customer_allowed(self):
        # Give the active user a funded source account
        active_source = _account(self.active_user, Decimal("500.00"))
        tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("100.00"),
            source_account=active_source,
            destination_account=self.source,
            customer=self.active_user,
        )
        self.assertEqual(tx.status, TransactionStatus.COMPLETED)
