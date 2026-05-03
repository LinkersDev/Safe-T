"""
Accounts app services — all write operations.

Design rules:
  - create_account is called by users.services.approve_user inside an atomic block.
  - freeze/block/unfreeze always update Account.status to stay in sync with
    the active AccountRestriction record.
  - No balance mutations happen here — all money movement goes through
    ledger.services.post_transaction.
"""
from __future__ import annotations

import logging
import random
import string
from decimal import Decimal

from django.db import transaction as db_transaction
from django.utils import timezone

from .constants import (
    ACCOUNT_NUMBER_LENGTH,
    DEFAULT_CURRENCY_CODE,
    AccountStatus,
    RestrictionSource,
    RestrictionType,
)
from .exceptions import (
    AccountAlreadyClosedError,
    AccountNotFoundError,
    BeneficiaryAlreadyExistsError,
    BeneficiaryNotFoundError,
    CurrencyNotFoundError,
)
from .models import Account, AccountRestriction, Beneficiary, Currency

logger = logging.getLogger("apps.accounts")


# ---------------------------------------------------------------------------
# Account number generation
# ---------------------------------------------------------------------------

def _generate_account_number() -> str:
    """16-digit numeric account number, never starting with 0."""
    first = str(random.randint(1, 9))
    rest = "".join(random.choices(string.digits, k=ACCOUNT_NUMBER_LENGTH - 1))
    return first + rest


def _unique_account_number(max_attempts: int = 10) -> str:
    for _ in range(max_attempts):
        number = _generate_account_number()
        if not Account.objects.filter(account_number=number).exists():
            return number
    raise RuntimeError("Could not generate a unique account number after retries.")


# ---------------------------------------------------------------------------
# Account creation
# ---------------------------------------------------------------------------

def create_account(
    *,
    user,
    currency_code: str = DEFAULT_CURRENCY_CODE,
    created_by=None,
) -> Account:
    """
    Provisions a new ACTIVE account for an approved user.

    Called automatically from users.services.approve_user inside
    the same atomic block — if account creation fails, the approval
    is also rolled back.
    """
    try:
        currency = Currency.objects.get(code=currency_code, is_active=True)
    except Currency.DoesNotExist:
        raise CurrencyNotFoundError(
            f"Currency '{currency_code}' not found or inactive. "
            "Ensure seed migration has been applied."
        )

    account_number = _unique_account_number()
    account = Account.objects.create(
        user=user,
        currency=currency,
        account_number=account_number,
        account_name=user.full_name,
        status=AccountStatus.ACTIVE,
        available_balance=Decimal("0.00"),
        ledger_balance=Decimal("0.00"),
        blocked_amount=Decimal("0.00"),
        created_by=created_by,
    )

    logger.info(
        "Account created | account_number=%s user_id=%s currency=%s",
        account_number,
        user.pk,
        currency_code,
    )
    return account


# ---------------------------------------------------------------------------
# Account restriction — freeze
# ---------------------------------------------------------------------------

def freeze_account(
    *,
    account: Account,
    reason: str,
    applied_by=None,
    source: str = RestrictionSource.RISK_OFFICER,
) -> AccountRestriction:
    """
    Freezes an account.
    - Deactivates any existing active FREEZE for this account first.
    - Sets Account.status = FROZEN.
    - BLOCK status is not altered here — a blocked account can only be unblocked.
    """
    if account.status == AccountStatus.CLOSED:
        raise AccountAlreadyClosedError("Cannot freeze a closed account.")

    with db_transaction.atomic():
        AccountRestriction.objects.filter(
            account=account,
            restriction_type=RestrictionType.FREEZE,
            is_active=True,
        ).update(is_active=False, ends_at=timezone.now())

        restriction = AccountRestriction.objects.create(
            account=account,
            restriction_type=RestrictionType.FREEZE,
            reason=reason,
            source=source,
            applied_by=applied_by,
            is_active=True,
        )
        Account.objects.filter(pk=account.pk).update(
            status=AccountStatus.FROZEN,
            updated_at=timezone.now(),
        )

    logger.warning(
        "Account frozen | account_id=%s reason=%s by=%s",
        account.pk,
        reason,
        getattr(applied_by, "pk", None),
    )
    return restriction


# ---------------------------------------------------------------------------
# Account restriction — block
# ---------------------------------------------------------------------------

def block_account(
    *,
    account: Account,
    reason: str,
    applied_by=None,
    source: str = RestrictionSource.ADMIN,
) -> AccountRestriction:
    """
    Blocks an account (more severe than freeze — requires Admin to reverse).
    Sets Account.status = BLOCKED.
    """
    if account.status == AccountStatus.CLOSED:
        raise AccountAlreadyClosedError("Cannot block a closed account.")

    with db_transaction.atomic():
        AccountRestriction.objects.filter(
            account=account,
            restriction_type=RestrictionType.BLOCK,
            is_active=True,
        ).update(is_active=False, ends_at=timezone.now())

        restriction = AccountRestriction.objects.create(
            account=account,
            restriction_type=RestrictionType.BLOCK,
            reason=reason,
            source=source,
            applied_by=applied_by,
            is_active=True,
        )
        Account.objects.filter(pk=account.pk).update(
            status=AccountStatus.BLOCKED,
            updated_at=timezone.now(),
        )

    logger.warning(
        "Account blocked | account_id=%s reason=%s by=%s",
        account.pk,
        reason,
        getattr(applied_by, "pk", None),
    )
    return restriction


# ---------------------------------------------------------------------------
# Account restriction — unfreeze
# ---------------------------------------------------------------------------

def unfreeze_account(
    *,
    account: Account,
    released_by=None,
) -> Account:
    """
    Lifts the active FREEZE restriction.
    Restores Account.status = ACTIVE.
    If the account was also BLOCKED, status remains BLOCKED.
    """
    with db_transaction.atomic():
        AccountRestriction.objects.filter(
            account=account,
            restriction_type=RestrictionType.FREEZE,
            is_active=True,
        ).update(
            is_active=False,
            ends_at=timezone.now(),
            released_by=released_by,
        )

        # Only restore ACTIVE if not simultaneously BLOCKED.
        # Use a filtered update against the DB value (not the stale in-memory object)
        # to avoid incorrect status comparisons after an earlier .update() call.
        still_blocked = AccountRestriction.objects.filter(
            account=account,
            restriction_type=RestrictionType.BLOCK,
            is_active=True,
        ).exists()

        if not still_blocked:
            Account.objects.filter(
                pk=account.pk,
                status=AccountStatus.FROZEN,
            ).update(
                status=AccountStatus.ACTIVE,
                updated_at=timezone.now(),
            )

    account.refresh_from_db()
    logger.info("Account unfrozen | account_id=%s by=%s", account.pk, getattr(released_by, "pk", None))
    return account


# ---------------------------------------------------------------------------
# Account restriction — unblock
# ---------------------------------------------------------------------------

def unblock_account(
    *,
    account: Account,
    released_by=None,
) -> Account:
    """
    Lifts the active BLOCK restriction (Admin only).
    Restores Account.status = ACTIVE (unless still FROZEN).
    """
    with db_transaction.atomic():
        AccountRestriction.objects.filter(
            account=account,
            restriction_type=RestrictionType.BLOCK,
            is_active=True,
        ).update(
            is_active=False,
            ends_at=timezone.now(),
            released_by=released_by,
        )

        still_frozen = AccountRestriction.objects.filter(
            account=account,
            restriction_type=RestrictionType.FREEZE,
            is_active=True,
        ).exists()

        if not still_frozen:
            Account.objects.filter(
                pk=account.pk,
                status=AccountStatus.BLOCKED,
            ).update(
                status=AccountStatus.ACTIVE,
                updated_at=timezone.now(),
            )

    account.refresh_from_db()
    logger.info("Account unblocked | account_id=%s by=%s", account.pk, getattr(released_by, "pk", None))
    return account


# ---------------------------------------------------------------------------
# Account close
# ---------------------------------------------------------------------------

def close_account(
    *,
    account: Account,
    reason: str,
    closed_by=None,
) -> Account:
    """
    Permanently closes an account.
    Zero-balance check is NOT enforced here — caller must verify balance
    before calling this (responsibility of the view layer).
    """
    if account.status == AccountStatus.CLOSED:
        raise AccountAlreadyClosedError("Account is already closed.")

    Account.objects.filter(pk=account.pk).update(
        status=AccountStatus.CLOSED,
        closed_at=timezone.now(),
        closed_reason=reason,
        updated_at=timezone.now(),
    )
    account.refresh_from_db()

    logger.warning(
        "Account closed | account_id=%s reason=%s by=%s",
        account.pk,
        reason,
        getattr(closed_by, "pk", None),
    )
    return account


# ---------------------------------------------------------------------------
# Beneficiaries
# ---------------------------------------------------------------------------

def add_beneficiary(
    *,
    owner,
    destination_account: Account,
    nickname: str,
) -> Beneficiary:
    """
    Saves a destination account as a beneficiary for quick transfers.
    Reactivates a previously deactivated entry instead of creating a duplicate.
    """
    try:
        existing = Beneficiary.objects.get(
            owner=owner,
            destination_account=destination_account,
        )
        if existing.is_active:
            raise BeneficiaryAlreadyExistsError(
                "This account is already an active beneficiary."
            )
        existing.is_active = True
        existing.nickname = nickname.strip()
        existing.save(update_fields=["is_active", "nickname"])
        return existing
    except Beneficiary.DoesNotExist:
        pass

    return Beneficiary.objects.create(
        owner=owner,
        destination_account=destination_account,
        nickname=nickname.strip(),
        is_active=True,
    )


def deactivate_beneficiary(*, beneficiary_id: int, user) -> Beneficiary:
    try:
        beneficiary = Beneficiary.objects.get(pk=beneficiary_id, owner=user)
    except Beneficiary.DoesNotExist:
        raise BeneficiaryNotFoundError("Beneficiary not found.")

    beneficiary.is_active = False
    beneficiary.save(update_fields=["is_active"])
    return beneficiary
