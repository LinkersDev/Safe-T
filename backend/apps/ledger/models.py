"""
Ledger app models: Transaction, TransactionEntry, TransactionHistory, FeeRule.

Balance invariants (enforced by post_transaction service, not at model level):
  - For every COMPLETED transaction: SUM(DEBIT + FEE amounts) == SUM(CREDIT amounts)
  - No COMPLETED transaction row is ever mutated — use reverse_transaction instead.
  - Balance fields on Account are updated only inside post_transaction's atomic block.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from .constants import (
    EntryType,
    FeeType,
    TransactionChannel,
    TransactionStatus,
    TransactionType,
)


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class Transaction(models.Model):
    """
    Represents one economic event.

    A transaction is immutable once COMPLETED — reversals create a new
    Transaction with parent_transaction pointing to the original.
    """
    reference_number = models.CharField(max_length=40, unique=True)
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.CHOICES,
    )
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.CHOICES,
        default=TransactionStatus.PENDING,
    )
    currency = models.ForeignKey(
        "accounts.Currency",
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    channel = models.CharField(
        max_length=30,
        choices=TransactionChannel.CHOICES,
        default=TransactionChannel.MOBILE,
    )

    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="initiated_transactions",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )

    requires_otp = models.BooleanField(default=False)
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Points to the original transaction for reversals
    parent_transaction = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reversals",
    )

    # Client-supplied key for idempotent submission
    idempotency_key = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )

    occurred_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reversed_at = models.DateTimeField(null=True, blank=True)

    failure_code = models.CharField(max_length=50, blank=True)
    failure_reason = models.TextField(blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "transactions"
        indexes = [
            models.Index(fields=["reference_number"]),
            models.Index(fields=["transaction_type", "status"]),
            models.Index(fields=["occurred_at"]),                     # time-series queries
            models.Index(fields=["customer", "occurred_at"]),
            models.Index(fields=["initiated_by", "occurred_at"]),
            models.Index(fields=["completed_at"]),
            models.Index(fields=["idempotency_key"]),
            models.Index(fields=["status", "occurred_at"]),           # reporting: completed tx by period
        ]

    def __str__(self) -> str:
        return f"{self.reference_number} [{self.transaction_type} {self.status}]"


# ---------------------------------------------------------------------------
# TransactionEntry
# ---------------------------------------------------------------------------

class TransactionEntry(models.Model):
    """
    One side of a double-entry ledger posting.

    For every COMPLETED transaction:
      SUM(entry.amount for DEBIT + FEE entries) == SUM(entry.amount for CREDIT entries)
    """
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="transaction_entries",
    )
    entry_type = models.CharField(
        max_length=10,
        choices=EntryType.CHOICES,
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    sequence_no = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transaction_entries"
        unique_together = [("transaction", "sequence_no")]
        indexes = [
            models.Index(fields=["account", "created_at"]),
            models.Index(fields=["entry_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.entry_type} {self.amount} on {self.account_id} "
            f"(tx={self.transaction_id})"
        )


# ---------------------------------------------------------------------------
# TransactionHistory
# ---------------------------------------------------------------------------

class TransactionHistory(models.Model):
    """
    Immutable archival snapshot of a completed transaction.
    Written once after COMPLETED; never updated.
    Exists to serve long-term reporting without JOIN-heavy queries.
    """
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.PROTECT,
        related_name="history",
    )
    reference_number = models.CharField(max_length=40)
    transaction_type = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    currency_code = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    payload_json = models.JSONField(default=dict)
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transaction_history"
        indexes = [
            models.Index(fields=["reference_number"]),
            models.Index(fields=["archived_at"]),
        ]

    def __str__(self) -> str:
        return f"Archive {self.reference_number} @ {self.archived_at}"


# ---------------------------------------------------------------------------
# FeeRule
# ---------------------------------------------------------------------------

class FeeRule(models.Model):
    """
    Defines how fees are computed for a given transaction type and currency.

    Fee = MAX(min_fee, MIN(max_fee, fixed_fee + (amount × percentage_fee)))

    Rules are selected by (transaction_type, currency, is_active) with the
    highest-priority active rule winning.
    """
    name = models.CharField(max_length=100)
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.CHOICES,
    )
    currency = models.ForeignKey(
        "accounts.Currency",
        on_delete=models.PROTECT,
        related_name="fee_rules",
    )

    # Tier bounds — rule only applies when min_amount <= tx_amount <= max_amount
    min_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
    )
    max_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Null = no upper limit on transaction amount.",
    )

    fixed_fee = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
    )
    percentage_fee = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("0"),
        help_text="e.g. 0.0150 for 1.50%",
    )

    # Computed fee bounds
    min_fee = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
    )
    max_fee = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Null = no cap on fee amount.",
    )

    priority = models.PositiveSmallIntegerField(
        default=100,
        help_text="Lower number = higher priority when multiple rules match.",
    )
    is_active = models.BooleanField(default=True)
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fee_rules"
        indexes = [
            models.Index(fields=["transaction_type", "currency", "is_active"]),
            models.Index(fields=["effective_from", "effective_to"]),
        ]
        ordering = ["priority"]

    def __str__(self) -> str:
        return (
            f"{self.name} [{self.transaction_type}/{self.currency_id}] "
            f"active={self.is_active}"
        )
