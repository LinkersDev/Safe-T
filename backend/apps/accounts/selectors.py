"""
Accounts app selectors — read-only queries.

assert_account_can_debit is placed here because it is a read-only guard
used by both this app (views) and ledger.services.post_transaction.
"""
from __future__ import annotations

from django.db.models import QuerySet

from .constants import AccountStatus
from .exceptions import AccountNotFoundError, AccountRestrictedError
from .models import Account, AccountRestriction, Beneficiary, Currency


def get_account_by_id(account_id: int) -> Account | None:
    try:
        return Account.objects.select_related("user", "currency").get(pk=account_id)
    except Account.DoesNotExist:
        return None


def get_account_by_number(account_number: str) -> Account | None:
    try:
        return Account.objects.select_related("user", "currency").get(
            account_number=account_number
        )
    except Account.DoesNotExist:
        return None


def get_accounts_for_user(user) -> QuerySet[Account]:
    return (
        Account.objects.select_related("currency")
        .filter(user=user)
        .order_by("opened_at")
    )


def assert_account_can_debit(account: Account) -> None:
    """
    Raises AccountRestrictedError if the account is FROZEN, BLOCKED, or CLOSED.

    This guard MUST be called by ledger.services.post_transaction:
      1. Before acquiring SELECT FOR UPDATE (fast-fail, no lock acquired)
      2. After acquiring SELECT FOR UPDATE (re-check after lock, race-condition safety)

    Only ledger service may read and update balances; this selector only
    checks the status field.
    """
    if account.status in AccountStatus.DEBIT_RESTRICTED:
        raise AccountRestrictedError(
            f"Account {account.account_number} cannot be debited: "
            f"status={account.status}"
        )


def assert_balance_sufficient(account: Account, amount) -> None:
    """
    Raises AccountRestrictedError if available_balance < amount.
    Caller must hold a SELECT FOR UPDATE lock on the account before calling this.
    """
    from decimal import Decimal
    if account.available_balance < Decimal(str(amount)):
        from .exceptions import InsufficientFundsError
        raise InsufficientFundsError(
            f"Insufficient funds: available={account.available_balance}, "
            f"requested={amount}"
        )


def get_active_restrictions(account: Account) -> QuerySet[AccountRestriction]:
    return AccountRestriction.objects.filter(account=account, is_active=True).order_by(
        "starts_at"
    )


def get_active_beneficiaries(user) -> QuerySet[Beneficiary]:
    return (
        Beneficiary.objects.select_related(
            "destination_account",
            "destination_account__currency",
            "destination_account__user",
        )
        .filter(owner=user, is_active=True)
        .order_by("nickname")
    )


def get_active_currencies() -> QuerySet[Currency]:
    return Currency.objects.filter(is_active=True).order_by("code")


def get_all_accounts_staff(filters: dict | None = None) -> QuerySet[Account]:
    """Staff-facing full account list with optional filters."""
    qs = Account.objects.select_related("user", "currency").order_by("-opened_at")
    if filters:
        if status := filters.get("status"):
            qs = qs.filter(status=status)
        if currency := filters.get("currency"):
            qs = qs.filter(currency_id=currency)
    return qs
