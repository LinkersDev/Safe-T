"""
Ledger write-path services.

Core contract:
  - post_transaction() is the ONLY function that mutates account balances.
  - All balance changes happen inside a single atomic() block with SELECT FOR UPDATE.
  - Double-entry invariant is asserted before the transaction status is set to COMPLETED.
  - No COMPLETED transaction row is mutated; use reverse_transaction() to undo.
"""
import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import transaction as db_transaction
from django.db.models import F
from django.utils import timezone

from apps.accounts.exceptions import InsufficientFundsError
from apps.accounts.models import Account
from apps.accounts.selectors import assert_account_can_debit
from apps.users.constants import KycStatus, UserStatus

from .constants import EntryType, TransactionChannel, TransactionStatus, TransactionType
from .exceptions import (
    DuplicateTransactionError,
    KYCNotApprovedError,
    TransactionAlreadyReversedError,
    TransactionBalanceError,
    TransactionNotFoundError,
    TransactionNotReversibleError,
    UserNotActiveError,
)
from .models import FeeRule, Transaction, TransactionEntry, TransactionHistory

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _reference_number(tx_type: str, max_attempts: int = 5) -> str:
    """Generate a unique reference number for the given transaction type."""
    prefix_map = {
        TransactionType.TRANSFER: "TRF",
        TransactionType.DEPOSIT: "DEP",
        TransactionType.WITHDRAWAL: "WTH",
        TransactionType.QR_PAYMENT: "QRP",
        TransactionType.BILL_PAYMENT: "BLP",
    }
    prefix = prefix_map.get(tx_type, "TXN")
    for _ in range(max_attempts):
        ref = f"{prefix}{uuid.uuid4().hex[:12].upper()}"
        if not Transaction.objects.filter(reference_number=ref).exists():
            return ref
    raise RuntimeError(  # pragma: no cover
        f"Failed to generate a unique reference number after {max_attempts} attempts."
    )


def _assert_entries_balanced(transaction: Transaction) -> None:
    """Raise TransactionBalanceError if debit and credit sides do not match."""
    entries = list(transaction.entries.all())
    debit_total = sum(
        e.amount for e in entries if e.entry_type in EntryType.DEBIT_TYPES
    )
    credit_total = sum(
        e.amount for e in entries if e.entry_type in EntryType.CREDIT_TYPES
    )
    if debit_total != credit_total:
        raise TransactionBalanceError(
            f"Transaction {transaction.reference_number} is unbalanced: "
            f"debits={debit_total}, credits={credit_total}."
        )


def _assert_user_active(user) -> None:
    """Raise UserNotActiveError for users that have not been fully activated."""
    if user is not None and user.status == UserStatus.PENDING_VERIFICATION:
        raise UserNotActiveError(
            "Monetary operations are not permitted for unverified accounts."
        )


def _assert_kyc_approved(user) -> None:
    """
    Defence-in-depth guard: raise KYCNotApprovedError when the customer has
    not completed identity verification.

    Called inside post_transaction() *before* any lock is acquired so that
    no database state is dirtied for rejected users.  The view layer adds a
    matching IsKYCApproved permission class, but this service-layer guard
    ensures the invariant holds even for direct service calls.
    """
    if user is None:
        return
    if user.kyc_status != KycStatus.APPROVED:
        raise KYCNotApprovedError(
            f"Financial operations require approved KYC. "
            f"Current status: {user.kyc_status}."
        )


# ---------------------------------------------------------------------------
# Fee calculation
# ---------------------------------------------------------------------------

def calculate_fee(
    *,
    transaction_type: str,
    currency_code: str,
    amount: Decimal,
) -> tuple[Decimal, "Account | None"]:
    """
    Return (fee_amount, fee_pool_account).

    fee_amount is 0 when:
      - No active FeeRule matches the criteria, or
      - LEDGER_FEE_POOL_ACCOUNT_NUMBER is not configured / account not found.

    Formula:  fee = fixed_fee + (amount × percentage_fee)
    Clamped:  fee = MAX(min_fee, MIN(max_fee, fee))  where max_fee=None means uncapped
    """
    from django.db.models import Q

    now = timezone.now()
    rule = (
        FeeRule.objects.filter(
            transaction_type=transaction_type,
            currency_id=currency_code,
            is_active=True,
            effective_from__lte=now,
            min_amount__lte=amount,
        )
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gt=now))
        .filter(Q(max_amount__isnull=True) | Q(max_amount__gte=amount))
        .order_by("priority")
        .first()
    )

    if rule is None:
        return Decimal("0"), None

    # Retrieve fee pool account
    fee_pool_number = getattr(settings, "LEDGER_FEE_POOL_ACCOUNT_NUMBER", "")
    if not fee_pool_number:
        logger.warning("FeeRule matched but LEDGER_FEE_POOL_ACCOUNT_NUMBER is not set; skipping fee.")
        return Decimal("0"), None

    fee_pool = Account.objects.filter(account_number=fee_pool_number).first()
    if fee_pool is None:
        logger.warning(
            "FeeRule matched but fee pool account %s not found; skipping fee.",
            fee_pool_number,
        )
        return Decimal("0"), None

    # Compute fee
    fee = rule.fixed_fee + (amount * rule.percentage_fee)
    fee = max(rule.min_fee, fee)
    if rule.max_fee is not None:
        fee = min(rule.max_fee, fee)

    return fee.quantize(Decimal("0.01")), fee_pool


# ---------------------------------------------------------------------------
# post_transaction — single atomic entry point for all balance changes
# ---------------------------------------------------------------------------

def post_transaction(
    *,
    transaction_type: str,
    currency_code: str,
    amount: Decimal,
    source_account: Account,
    destination_account: Account,
    description: str = "",
    channel: str = TransactionChannel.MOBILE,
    initiated_by=None,
    customer=None,
    idempotency_key: str | None = None,
    requires_otp: bool = False,
    otp_verified_at=None,
    metadata: dict | None = None,
) -> Transaction:
    """
    Post a monetary transaction atomically.

    Guarantees:
      1. source_account and destination_account are locked with SELECT FOR UPDATE
         in ascending primary-key order (deadlock prevention).
      2. Balance sufficiency is re-checked *after* acquiring locks.
      3. Double-entry balance is asserted before the COMPLETED status is set.
      4. PENDING_VERIFICATION customers are rejected before any DB write.

    Returns the created (and COMPLETED) Transaction object.
    """
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("Transaction amount must be positive.")

    if source_account.pk == destination_account.pk:
        raise ValueError("Source and destination accounts must differ.")

    # Pending-user guard — fast fail before any locking
    _assert_user_active(customer)

    # KYC guard — customer must have completed identity verification
    _assert_kyc_approved(customer)

    # Pre-lock debit check (avoids locking accounts that will always fail)
    assert_account_can_debit(source_account)

    # Idempotency: return existing COMPLETED; error on in-flight duplicate
    if idempotency_key:
        existing = Transaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            if existing.status == TransactionStatus.COMPLETED:
                return existing
            if existing.status == TransactionStatus.PROCESSING:
                raise DuplicateTransactionError(
                    f"Transaction with key '{idempotency_key}' is currently processing."
                )

    with db_transaction.atomic():
        # Lock both accounts in deterministic order to prevent deadlock
        sorted_pks = sorted([source_account.pk, destination_account.pk])
        locked_map: dict[int, Account] = {
            acc.pk: acc
            for acc in Account.objects.select_for_update().filter(pk__in=sorted_pks)
        }
        locked_source = locked_map[source_account.pk]
        locked_dest = locked_map[destination_account.pk]

        # Re-validate source status after acquiring the lock
        assert_account_can_debit(locked_source)

        # Fee calculation happens inside the lock so the pool account is also lockable
        fee_amount, fee_pool = calculate_fee(
            transaction_type=transaction_type,
            currency_code=currency_code,
            amount=amount,
        )
        total_debit = amount + fee_amount

        # Balance sufficiency check (post-lock)
        if locked_source.available_balance < total_debit:
            raise InsufficientFundsError(
                f"Insufficient funds: available={locked_source.available_balance}, "
                f"required={total_debit}."
            )

        # Lock fee pool account if applicable
        locked_fee_pool = None
        if fee_amount > 0 and fee_pool is not None:
            locked_fee_pool = (
                Account.objects.select_for_update()
                .filter(pk=fee_pool.pk)
                .first()
            )

        # Create transaction in PROCESSING
        reference = _reference_number(transaction_type)
        transaction = Transaction.objects.create(
            reference_number=reference,
            transaction_type=transaction_type,
            status=TransactionStatus.PROCESSING,
            currency_id=currency_code,
            amount=amount,
            description=description,
            channel=channel,
            initiated_by=initiated_by,
            customer=customer,
            requires_otp=requires_otp,
            otp_verified_at=otp_verified_at,
            idempotency_key=idempotency_key,
            metadata_json=metadata or {},
        )

        # Build entry list
        entries = [
            TransactionEntry(
                transaction=transaction,
                account=locked_source,
                entry_type=EntryType.DEBIT,
                amount=amount,
                sequence_no=1,
            ),
            TransactionEntry(
                transaction=transaction,
                account=locked_dest,
                entry_type=EntryType.CREDIT,
                amount=amount,
                sequence_no=2,
            ),
        ]
        if fee_amount > 0 and locked_fee_pool is not None:
            entries += [
                TransactionEntry(
                    transaction=transaction,
                    account=locked_source,
                    entry_type=EntryType.FEE,
                    amount=fee_amount,
                    sequence_no=3,
                ),
                TransactionEntry(
                    transaction=transaction,
                    account=locked_fee_pool,
                    entry_type=EntryType.CREDIT,
                    amount=fee_amount,
                    sequence_no=4,
                ),
            ]

        TransactionEntry.objects.bulk_create(entries)

        # Assert double-entry balance before committing
        _assert_entries_balanced(transaction)

        # Apply balance changes
        now = timezone.now()
        Account.objects.filter(pk=locked_source.pk).update(
            available_balance=F("available_balance") - total_debit,
            ledger_balance=F("ledger_balance") - total_debit,
            updated_at=now,
        )
        Account.objects.filter(pk=locked_dest.pk).update(
            available_balance=F("available_balance") + amount,
            ledger_balance=F("ledger_balance") + amount,
            updated_at=now,
        )
        if fee_amount > 0 and locked_fee_pool is not None:
            Account.objects.filter(pk=locked_fee_pool.pk).update(
                available_balance=F("available_balance") + fee_amount,
                ledger_balance=F("ledger_balance") + fee_amount,
                updated_at=now,
            )

        # Complete the transaction
        Transaction.objects.filter(pk=transaction.pk).update(
            status=TransactionStatus.COMPLETED,
            completed_at=now,
        )
        transaction.refresh_from_db()

    # Post-commit: dispatch notifications (import deferred to avoid circular imports)
    _tx_pk = transaction.pk

    def _post_commit():
        try:
            from apps.support.services import dispatch_post_transaction_notifications
            dispatch_post_transaction_notifications(_tx_pk)
        except Exception:
            pass  # notification failure must never surface after the tx has committed

        try:
            from apps.risk.services import score_transaction
            score_transaction(_tx_pk)
        except Exception:
            pass  # risk scoring failure must never surface after the tx has committed

    db_transaction.on_commit(_post_commit)

    return transaction


# ---------------------------------------------------------------------------
# reverse_transaction
# ---------------------------------------------------------------------------

def reverse_transaction(
    *,
    reference_number: str,
    reason: str,
    initiated_by=None,
) -> Transaction:
    """
    Create a reversal for a COMPLETED transaction.

    The original transaction is never mutated (except setting reversed_at).
    A new Transaction with parent_transaction=original is created with
    swapped entries.

    Reversal does NOT re-check destination balances — staff-level operation.
    """
    original = (
        Transaction.objects.filter(reference_number=reference_number)
        .prefetch_related("entries__account")
        .first()
    )
    if original is None:
        raise TransactionNotFoundError(
            f"Transaction '{reference_number}' not found."
        )
    if original.reversed_at is not None or original.status == TransactionStatus.REVERSED:
        raise TransactionAlreadyReversedError(
            f"Transaction '{reference_number}' has already been reversed."
        )
    if original.status != TransactionStatus.COMPLETED:
        raise TransactionNotReversibleError(
            f"Only COMPLETED transactions can be reversed (status={original.status})."
        )

    original_entries = list(original.entries.select_related("account").all())
    account_pks = sorted({e.account_id for e in original_entries})

    # Entry-type swap: DEBIT→CREDIT, CREDIT→DEBIT, FEE→CREDIT (fee returned)
    swap = {
        EntryType.DEBIT: EntryType.CREDIT,
        EntryType.CREDIT: EntryType.DEBIT,
        EntryType.FEE: EntryType.CREDIT,
    }

    with db_transaction.atomic():
        locked_map: dict[int, Account] = {
            acc.pk: acc
            for acc in Account.objects.select_for_update().filter(pk__in=account_pks)
        }

        reversal_ref = _reference_number(original.transaction_type)
        reversal = Transaction.objects.create(
            reference_number=reversal_ref,
            transaction_type=original.transaction_type,
            status=TransactionStatus.COMPLETED,
            currency_id=original.currency_id,
            amount=original.amount,
            description=f"REVERSAL: {reason}",
            channel=original.channel,
            initiated_by=initiated_by,
            customer=original.customer,
            parent_transaction=original,
            completed_at=timezone.now(),
            metadata_json={
                "reversal_reason": reason,
                "original_reference": original.reference_number,
            },
        )

        reversal_entries = [
            TransactionEntry(
                transaction=reversal,
                account=locked_map[e.account_id],
                entry_type=swap[e.entry_type],
                amount=e.amount,
                sequence_no=e.sequence_no,
            )
            for e in original_entries
        ]
        TransactionEntry.objects.bulk_create(reversal_entries)

        _assert_entries_balanced(reversal)

        # Reverse balance changes
        now = timezone.now()
        for entry in original_entries:
            if entry.entry_type in EntryType.DEBIT_TYPES:
                # Was a debit → credit it back
                Account.objects.filter(pk=entry.account_id).update(
                    available_balance=F("available_balance") + entry.amount,
                    ledger_balance=F("ledger_balance") + entry.amount,
                    updated_at=now,
                )
            elif entry.entry_type in EntryType.CREDIT_TYPES:
                # Was a credit → debit it back
                Account.objects.filter(pk=entry.account_id).update(
                    available_balance=F("available_balance") - entry.amount,
                    ledger_balance=F("ledger_balance") - entry.amount,
                    updated_at=now,
                )

        # Mark the original as reversed (one-time, safe mutation)
        Transaction.objects.filter(pk=original.pk).update(
            status=TransactionStatus.REVERSED,
            reversed_at=now,
        )

    return reversal


# ---------------------------------------------------------------------------
# archive_transaction
# ---------------------------------------------------------------------------

def archive_transaction(transaction: Transaction) -> TransactionHistory:
    """
    Write an immutable archival snapshot of a COMPLETED transaction.

    Idempotent — returns the existing history record if already archived.
    """
    existing = TransactionHistory.objects.filter(transaction=transaction).first()
    if existing:
        return existing

    entries_snapshot = [
        {
            "entry_type": e["entry_type"],
            "amount": str(e["amount"]),
            "sequence_no": e["sequence_no"],
            "account_id": e["account_id"],
        }
        for e in transaction.entries.values("entry_type", "amount", "sequence_no", "account_id")
    ]

    return TransactionHistory.objects.create(
        transaction=transaction,
        reference_number=transaction.reference_number,
        transaction_type=transaction.transaction_type,
        status=transaction.status,
        currency_code=transaction.currency_id,
        amount=transaction.amount,
        payload_json={
            "description": transaction.description,
            "channel": transaction.channel,
            "customer_id": transaction.customer_id,
            "entries": entries_snapshot,
        },
    )
