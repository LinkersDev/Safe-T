"""
Unit + integration tests for accounts.services and accounts.selectors.

Run:
    python manage.py test apps.accounts.tests.test_services \
        --settings=config.settings.test --verbosity=2
"""
from decimal import Decimal

from django.test import TestCase

from apps.users.constants import RoleCode, UserStatus
from apps.users.models import Role, User

from apps.accounts.constants import AccountStatus, RestrictionType, DEFAULT_CURRENCY_CODE
from apps.accounts.exceptions import (
    AccountAlreadyClosedError,
    AccountRestrictedError,
    BeneficiaryAlreadyExistsError,
    BeneficiaryNotFoundError,
    InsufficientFundsError,
)
from apps.accounts.models import Account, AccountRestriction, Beneficiary, Currency
from apps.accounts.selectors import (
    assert_account_can_debit,
    assert_balance_sufficient,
    get_account_by_number,
    get_accounts_for_user,
    get_active_beneficiaries,
)
from apps.accounts.services import (
    add_beneficiary,
    block_account,
    close_account,
    create_account,
    deactivate_beneficiary,
    freeze_account,
    unblock_account,
    unfreeze_account,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(phone="+966501100001"):
    role, _ = Role.objects.get_or_create(
        code=RoleCode.CUSTOMER,
        defaults={"name": "Customer", "is_staff_role": False, "is_system_role": True},
    )
    user = User(
        phone_number=phone,
        phone_number_normalized=phone,
        full_name="Account Tester",
        role=role,
        status=UserStatus.ACTIVE,
        is_active=True,
    )
    user.set_password("Pass1234!")
    user.save()
    return user


def _make_account(user=None, status=AccountStatus.ACTIVE) -> Account:
    if user is None:
        user = _make_user("+966501100002")
    account = create_account(user=user)
    if status != AccountStatus.ACTIVE:
        Account.objects.filter(pk=account.pk).update(status=status)
        account.refresh_from_db()
    return account


# ===========================================================================
# create_account
# ===========================================================================

class CreateAccountTests(TestCase):

    def test_creates_account_with_correct_defaults(self):
        user = _make_user("+966501100010")
        account = create_account(user=user)
        self.assertEqual(account.status, AccountStatus.ACTIVE)
        self.assertEqual(account.available_balance, Decimal("0.00"))
        self.assertEqual(account.ledger_balance, Decimal("0.00"))
        self.assertEqual(account.blocked_amount, Decimal("0.00"))
        self.assertEqual(account.currency.code, DEFAULT_CURRENCY_CODE)
        self.assertEqual(account.account_name, user.full_name)

    def test_account_number_is_16_digits(self):
        account = create_account(user=_make_user("+966501100011"))
        self.assertEqual(len(account.account_number), 16)
        self.assertTrue(account.account_number.isdigit())
        self.assertNotEqual(account.account_number[0], "0")

    def test_account_number_is_unique(self):
        u1 = _make_user("+966501100012")
        u2 = _make_user("+966501100013")
        a1 = create_account(user=u1)
        a2 = create_account(user=u2)
        self.assertNotEqual(a1.account_number, a2.account_number)

    def test_account_is_linked_to_user(self):
        user = _make_user("+966501100014")
        account = create_account(user=user)
        self.assertEqual(account.user_id, user.pk)


# ===========================================================================
# freeze / unfreeze
# ===========================================================================

class FreezeUnfreezeTests(TestCase):

    def setUp(self):
        self.account = _make_account()

    def test_freeze_sets_status_to_frozen(self):
        freeze_account(account=self.account, reason="Suspicious activity")
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.FROZEN)

    def test_freeze_creates_active_restriction(self):
        freeze_account(account=self.account, reason="Test freeze")
        restriction = AccountRestriction.objects.filter(
            account=self.account,
            restriction_type=RestrictionType.FREEZE,
            is_active=True,
        ).first()
        self.assertIsNotNone(restriction)
        self.assertEqual(restriction.reason, "Test freeze")

    def test_freeze_cancels_previous_freeze(self):
        freeze_account(account=self.account, reason="First freeze")
        freeze_account(account=self.account, reason="Second freeze")
        active_count = AccountRestriction.objects.filter(
            account=self.account, restriction_type=RestrictionType.FREEZE, is_active=True
        ).count()
        self.assertEqual(active_count, 1)

    def test_unfreeze_restores_active_status(self):
        freeze_account(account=self.account, reason="Test")
        unfreeze_account(account=self.account)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.ACTIVE)

    def test_unfreeze_deactivates_restriction(self):
        freeze_account(account=self.account, reason="Test")
        unfreeze_account(account=self.account)
        active = AccountRestriction.objects.filter(
            account=self.account, restriction_type=RestrictionType.FREEZE, is_active=True
        ).exists()
        self.assertFalse(active)

    def test_cannot_freeze_closed_account(self):
        Account.objects.filter(pk=self.account.pk).update(status=AccountStatus.CLOSED)
        self.account.refresh_from_db()
        with self.assertRaises(AccountAlreadyClosedError):
            freeze_account(account=self.account, reason="Test")


# ===========================================================================
# block / unblock
# ===========================================================================

class BlockUnblockTests(TestCase):

    def setUp(self):
        self.account = _make_account()

    def test_block_sets_status_to_blocked(self):
        block_account(account=self.account, reason="Fraud detected")
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.BLOCKED)

    def test_block_creates_active_restriction(self):
        block_account(account=self.account, reason="Test block")
        restriction = AccountRestriction.objects.filter(
            account=self.account, restriction_type=RestrictionType.BLOCK, is_active=True
        ).first()
        self.assertIsNotNone(restriction)

    def test_unblock_restores_active_status(self):
        block_account(account=self.account, reason="Test")
        unblock_account(account=self.account)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.ACTIVE)

    def test_unfreeze_does_not_restore_if_still_blocked(self):
        """
        If an account is both FROZEN and BLOCKED, unfreezing should NOT
        restore ACTIVE status — the BLOCK remains.
        """
        freeze_account(account=self.account, reason="Freeze")
        block_account(account=self.account, reason="Block")
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.BLOCKED)

        unfreeze_account(account=self.account)
        self.account.refresh_from_db()
        # Status must remain BLOCKED because the block is still active
        self.assertEqual(self.account.status, AccountStatus.BLOCKED)


# ===========================================================================
# close
# ===========================================================================

class CloseAccountTests(TestCase):

    def setUp(self):
        self.account = _make_account()

    def test_close_sets_status_and_timestamp(self):
        close_account(account=self.account, reason="Customer request")
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.CLOSED)
        self.assertIsNotNone(self.account.closed_at)
        self.assertEqual(self.account.closed_reason, "Customer request")

    def test_close_already_closed_raises_error(self):
        close_account(account=self.account, reason="First close")
        self.account.refresh_from_db()
        with self.assertRaises(AccountAlreadyClosedError):
            close_account(account=self.account, reason="Second close")


# ===========================================================================
# assert_account_can_debit
# ===========================================================================

class AssertAccountCanDebitTests(TestCase):

    def setUp(self):
        self.account = _make_account()

    def test_active_account_does_not_raise(self):
        # Should not raise
        assert_account_can_debit(self.account)

    def test_frozen_account_raises(self):
        Account.objects.filter(pk=self.account.pk).update(status=AccountStatus.FROZEN)
        self.account.refresh_from_db()
        with self.assertRaises(AccountRestrictedError):
            assert_account_can_debit(self.account)

    def test_blocked_account_raises(self):
        Account.objects.filter(pk=self.account.pk).update(status=AccountStatus.BLOCKED)
        self.account.refresh_from_db()
        with self.assertRaises(AccountRestrictedError):
            assert_account_can_debit(self.account)

    def test_closed_account_raises(self):
        Account.objects.filter(pk=self.account.pk).update(status=AccountStatus.CLOSED)
        self.account.refresh_from_db()
        with self.assertRaises(AccountRestrictedError):
            assert_account_can_debit(self.account)


# ===========================================================================
# assert_balance_sufficient
# ===========================================================================

class AssertBalanceSufficientTests(TestCase):

    def setUp(self):
        self.account = _make_account()

    def test_exact_balance_does_not_raise(self):
        Account.objects.filter(pk=self.account.pk).update(
            available_balance=Decimal("100.00")
        )
        self.account.refresh_from_db()
        assert_balance_sufficient(self.account, Decimal("100.00"))

    def test_insufficient_balance_raises(self):
        Account.objects.filter(pk=self.account.pk).update(
            available_balance=Decimal("50.00")
        )
        self.account.refresh_from_db()
        with self.assertRaises(InsufficientFundsError):
            assert_balance_sufficient(self.account, Decimal("100.00"))


# ===========================================================================
# beneficiaries
# ===========================================================================

class BeneficiaryTests(TestCase):

    def setUp(self):
        self.owner = _make_user("+966501100030")
        self.dest_user = _make_user("+966501100031")
        self.dest_account = create_account(user=self.dest_user)

    def test_add_beneficiary_creates_record(self):
        b = add_beneficiary(
            owner=self.owner,
            destination_account=self.dest_account,
            nickname="Friend",
        )
        self.assertTrue(b.is_active)
        self.assertEqual(b.nickname, "Friend")

    def test_duplicate_active_beneficiary_raises(self):
        add_beneficiary(
            owner=self.owner,
            destination_account=self.dest_account,
            nickname="Friend",
        )
        with self.assertRaises(BeneficiaryAlreadyExistsError):
            add_beneficiary(
                owner=self.owner,
                destination_account=self.dest_account,
                nickname="Same account",
            )

    def test_reactivating_inactive_beneficiary_does_not_duplicate(self):
        b = add_beneficiary(
            owner=self.owner,
            destination_account=self.dest_account,
            nickname="First",
        )
        deactivate_beneficiary(beneficiary_id=b.pk, user=self.owner)
        b2 = add_beneficiary(
            owner=self.owner,
            destination_account=self.dest_account,
            nickname="Re-added",
        )
        self.assertEqual(b.pk, b2.pk)
        self.assertEqual(b2.nickname, "Re-added")

    def test_deactivate_beneficiary_sets_is_active_false(self):
        b = add_beneficiary(
            owner=self.owner,
            destination_account=self.dest_account,
            nickname="Test",
        )
        deactivate_beneficiary(beneficiary_id=b.pk, user=self.owner)
        b.refresh_from_db()
        self.assertFalse(b.is_active)

    def test_get_active_beneficiaries_excludes_inactive(self):
        b = add_beneficiary(
            owner=self.owner,
            destination_account=self.dest_account,
            nickname="Test",
        )
        deactivate_beneficiary(beneficiary_id=b.pk, user=self.owner)
        active = list(get_active_beneficiaries(self.owner))
        self.assertEqual(len(active), 0)

    def test_deactivate_wrong_owner_raises(self):
        b = add_beneficiary(
            owner=self.owner,
            destination_account=self.dest_account,
            nickname="Test",
        )
        other_user = _make_user("+966501100032")
        with self.assertRaises(BeneficiaryNotFoundError):
            deactivate_beneficiary(beneficiary_id=b.pk, user=other_user)


# ===========================================================================
# approve_user → create_account (integration)
# ===========================================================================

class ApproveUserCreatesAccountTests(TestCase):
    """
    Validates the wiring: when a user is approved, their bank account
    is created atomically in the same transaction.
    """

    def setUp(self):
        self.teller_role, _ = Role.objects.get_or_create(
            code=RoleCode.TELLER,
            defaults={"name": "Teller", "is_staff_role": True, "is_system_role": True},
        )
        self.customer_role, _ = Role.objects.get_or_create(
            code=RoleCode.CUSTOMER,
            defaults={"name": "Customer", "is_staff_role": False, "is_system_role": True},
        )
        self.teller = User(
            phone_number="+966501100040",
            phone_number_normalized="+966501100040",
            full_name="Test Teller",
            role=self.teller_role,
            status=UserStatus.ACTIVE,
            is_active=True,
        )
        self.teller.set_password("TellerPass1!")
        self.teller.save()

        self.customer = User(
            phone_number="+966501100041",
            phone_number_normalized="+966501100041",
            full_name="Test Customer",
            role=self.customer_role,
            status=UserStatus.PENDING_VERIFICATION,
            is_active=True,
        )
        self.customer.set_password("CustomerPass1!")
        self.customer.save()

    def test_approve_user_creates_account(self):
        from apps.users.services import approve_user
        approve_user(user_id=self.customer.pk, staff_user=self.teller)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.status, UserStatus.ACTIVE)

        accounts = Account.objects.filter(user=self.customer)
        self.assertEqual(accounts.count(), 1)
        self.assertEqual(accounts.first().status, AccountStatus.ACTIVE)
        self.assertEqual(accounts.first().currency.code, DEFAULT_CURRENCY_CODE)
