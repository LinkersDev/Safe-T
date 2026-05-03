"""
Accounts app models: Currency, Account, AccountRestriction, Beneficiary.

Balance rules (enforced by ledger service, not model-level):
  - available_balance >= 0 at all times
  - ledger_balance >= available_balance
  - blocked_amount represents reserved funds not yet moved
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from .constants import AccountStatus, RestrictionSource, RestrictionType


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------

class Currency(models.Model):
    """
    ISO 4217 currency.
    Primary key is the 3-letter currency code (e.g. 'USD').
    """
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10, blank=True)
    decimal_places = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "currencies"
        indexes = [
            models.Index(fields=["is_active"]),
        ]
        verbose_name_plural = "currencies"

    def __str__(self) -> str:
        return f"{self.code} ({self.name})"


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

class Account(models.Model):
    """
    A customer's bank account.

    Balance fields:
      available_balance — immediately updated on every debit/credit;
                          used for sufficiency checks before locking.
      ledger_balance    — tracks total posted debits and credits.
      blocked_amount    — funds reserved by HOLD entries; not yet moved.

    Only the ledger service (post_transaction) may update balance fields.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    account_number = models.CharField(max_length=34, unique=True)
    account_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=AccountStatus.CHOICES,
        default=AccountStatus.ACTIVE,
    )

    available_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    ledger_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    blocked_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_reason = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_accounts",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts"
        indexes = [
            models.Index(fields=["account_number"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["currency", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.account_number} [{self.status}] ({self.user_id})"


# ---------------------------------------------------------------------------
# AccountRestriction
# ---------------------------------------------------------------------------

class AccountRestriction(models.Model):
    """
    Append-only record of every FREEZE or BLOCK applied to an account.

    When a restriction is resolved (unfreeze/unblock), is_active is set to
    False and ends_at + released_by are recorded.
    Account.status is always kept in sync with the latest active restriction.
    """
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="restrictions",
    )
    restriction_type = models.CharField(
        max_length=20,
        choices=RestrictionType.CHOICES,
    )
    reason = models.TextField()
    source = models.CharField(
        max_length=30,
        choices=RestrictionSource.CHOICES,
        default=RestrictionSource.RISK_OFFICER,
    )

    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="applied_restrictions",
    )
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="released_restrictions",
    )

    starts_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "account_restrictions"
        indexes = [
            models.Index(fields=["account", "is_active"]),
            models.Index(fields=["restriction_type", "is_active"]),
            models.Index(fields=["starts_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.restriction_type} on {self.account_id} (active={self.is_active})"


# ---------------------------------------------------------------------------
# Beneficiary
# ---------------------------------------------------------------------------

class Beneficiary(models.Model):
    """
    A saved destination account for quick transfers.
    One owner can have only one active beneficiary per destination account.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="beneficiaries",
    )
    destination_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="as_beneficiary",
    )
    nickname = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "beneficiaries"
        unique_together = [("owner", "destination_account")]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.owner_id} → {self.destination_account_id} ({self.nickname})"
