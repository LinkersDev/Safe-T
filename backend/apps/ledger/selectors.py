"""Read-only queries for the ledger app."""
from django.db.models import Prefetch, QuerySet
from django.db.models import Q

from .models import Transaction, TransactionEntry, TransactionHistory


def get_transaction_by_reference(reference_number: str) -> Transaction | None:
    return (
        Transaction.objects.filter(reference_number=reference_number)
        .select_related("currency", "customer", "initiated_by", "parent_transaction")
        .prefetch_related("entries__account__user")
        .first()
    )


def get_transactions_for_account(
    account,
    *,
    limit: int = 50,
    offset: int = 0,
) -> QuerySet:
    """Return all entries linked to the given account, newest first."""
    return (
        TransactionEntry.objects.filter(account=account)
        .select_related("transaction__currency")
        .order_by("-created_at")[offset : offset + limit]
    )


def get_transactions_for_customer(
    customer,
    *,
    status: str | None = None,
    transaction_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> QuerySet:
    entry_qs = TransactionEntry.objects.select_related("account__user").order_by("sequence_no")
    qs = (
        Transaction.objects.filter(
            Q(customer=customer) | Q(entries__account__user=customer)
        )
        .select_related("currency", "initiated_by")
        .prefetch_related(Prefetch("entries", queryset=entry_qs))
        .distinct()
    )
    if status:
        qs = qs.filter(status=status)
    if transaction_type:
        qs = qs.filter(transaction_type=transaction_type)
    return qs.order_by("-occurred_at")[offset : offset + limit]


def get_all_transactions_staff(
    *,
    status: str | None = None,
    transaction_type: str | None = None,
    currency_code: str | None = None,
    q: str | None = None,
    occurred_from=None,
    occurred_to=None,
    limit: int = 100,
    offset: int = 0,
) -> QuerySet:
    qs = Transaction.objects.select_related("currency", "customer", "initiated_by")
    if status:
        qs = qs.filter(status=status)
    if transaction_type:
        qs = qs.filter(transaction_type=transaction_type)
    if currency_code:
        qs = qs.filter(currency_id=currency_code)
    if occurred_from:
        qs = qs.filter(occurred_at__gte=occurred_from)
    if occurred_to:
        qs = qs.filter(occurred_at__lte=occurred_to)
    if q:
        qv = (q or "").strip()
        if qv:
            # Match reference substring OR customer phone substring.
            qs = qs.filter(
                Q(reference_number__icontains=qv)
                | Q(customer__phone_number__icontains=qv)
                | Q(customer__phone_number_normalized__icontains=qv)
            )
    return qs.order_by("-occurred_at")[offset : offset + limit]


def get_transaction_entries(transaction: Transaction) -> QuerySet:
    return (
        TransactionEntry.objects.filter(transaction=transaction)
        .select_related("account")
        .order_by("sequence_no")
    )


def get_transaction_history(transaction: Transaction) -> TransactionHistory | None:
    return TransactionHistory.objects.filter(transaction=transaction).first()
