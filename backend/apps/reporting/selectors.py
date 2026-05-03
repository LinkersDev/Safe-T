"""
Reporting selectors — all read-only, aggregated queries.

Organised by consumer role:
  - Admin        : financial + user overview
  - Risk Officer : fraud metrics and alert summary
  - Operations   : KYC queue, support queue, recent activity
  - Audit        : deep-trace views for individual records

Performance notes:
  - All aggregations use DB-level SUM / COUNT via ORM — no Python loops.
  - Window: queries accept an explicit `days` / `weeks` parameter so callers
    can choose coarse or fine-grained resolution without extra indexes.
  - SELECT-related / prefetch_related is used on joins that touch multiple tables.
  - No business logic is performed here — selectors are pure readers.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.db.models.functions import TruncDay, TruncWeek
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------

def get_admin_summary() -> dict:
    """
    High-level platform snapshot for the Admin role.
    Returns a single dict of scalar metrics (no pagination needed).
    """
    from apps.accounts.models import Account
    from apps.ledger.constants import EntryType, TransactionStatus
    from apps.ledger.models import Transaction, TransactionEntry
    from apps.users.constants import UserStatus
    from apps.users.models import User

    user_stats = User.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=UserStatus.ACTIVE)),
        pending=Count("id", filter=Q(status=UserStatus.PENDING_VERIFICATION)),
        blocked=Count("id", filter=Q(status=UserStatus.BLOCKED)),
    )

    tx_stats = Transaction.objects.filter(
        status=TransactionStatus.COMPLETED
    ).aggregate(
        count=Count("id"),
        volume=Sum("amount"),
    )

    balance_stats = Account.objects.filter(
        status="ACTIVE"
    ).aggregate(
        total_available=Sum("available_balance"),
        total_ledger=Sum("ledger_balance"),
    )

    fee_stats = TransactionEntry.objects.filter(
        entry_type=EntryType.FEE,
        transaction__status=TransactionStatus.COMPLETED,
    ).aggregate(total=Sum("amount"))

    return {
        "total_users":               user_stats["total"]         or 0,
        "active_users":              user_stats["active"]        or 0,
        "pending_users":             user_stats["pending"]       or 0,
        "blocked_users":             user_stats["blocked"]       or 0,
        "total_transaction_count":   tx_stats["count"]           or 0,
        "total_transaction_volume":  tx_stats["volume"]          or Decimal("0"),
        "total_available_balance":   balance_stats["total_available"] or Decimal("0"),
        "total_ledger_balance":      balance_stats["total_ledger"]    or Decimal("0"),
        "fee_revenue":               fee_stats["total"]          or Decimal("0"),
    }


# ---------------------------------------------------------------------------
# Risk Officer dashboard
# ---------------------------------------------------------------------------

def get_risk_summary() -> dict:
    """Overview for the Risk Officer dashboard."""
    from apps.risk.constants import AlertSeverity, AlertStatus, AlertType
    from apps.risk.models import FraudAlert

    base = FraudAlert.objects

    open_count = base.filter(status=AlertStatus.OPEN).count()
    total      = base.count()

    by_severity = {
        sev: base.filter(severity=sev).count()
        for sev in [AlertSeverity.MEDIUM, AlertSeverity.HIGH, AlertSeverity.CRITICAL]
    }
    by_type = {
        t: base.filter(alert_type=t).count()
        for t, _ in AlertType.CHOICES
    }

    auto_actioned = base.exclude(auto_action_taken="").count()

    return {
        "open_alerts":       open_count,
        "total_alerts":      total,
        "by_severity":       by_severity,
        "by_type":           by_type,
        "auto_actioned":     auto_actioned,
    }


def get_fraud_metrics(*, days: int = 30) -> dict:
    """Time-series fraud metrics for Risk Officer reports."""
    from apps.risk.constants import AlertSeverity, AlertStatus
    from apps.risk.models import FraudAlert

    since = timezone.now() - timedelta(days=days)
    qs = FraudAlert.objects.filter(created_at__gte=since)

    total    = qs.count()
    critical = qs.filter(severity=AlertSeverity.CRITICAL).count()
    frozen   = qs.filter(auto_action_taken="ACCOUNT_FROZEN").count()
    resolved = qs.exclude(status=AlertStatus.OPEN).count()

    by_day = list(
        qs
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    return {
        "period_days":         days,
        "total_alerts":        total,
        "critical_alerts":     critical,
        "auto_frozen_accounts": frozen,
        "resolved_alerts":     resolved,
        "resolution_rate_pct": round(resolved / total * 100, 1) if total else 0.0,
        "by_day":              by_day,
    }


# ---------------------------------------------------------------------------
# Operations (Teller / Admin) dashboard
# ---------------------------------------------------------------------------

def get_operations_summary() -> dict:
    """Snapshot for operations staff: KYC queue, support queue, recent activity."""
    from apps.kyc.constants import KycDocumentStatus
    from apps.kyc.models import KycDocument
    from apps.ledger.constants import TransactionStatus
    from apps.ledger.models import Transaction
    from apps.support.constants import TicketStatus
    from apps.support.models import SupportTicket
    from apps.users.constants import KycStatus
    from apps.users.models import User

    pending_kyc_users = User.objects.filter(kyc_status=KycStatus.PENDING).count()
    pending_kyc_docs  = KycDocument.objects.filter(status=KycDocumentStatus.PENDING).count()

    open_tickets       = SupportTicket.objects.filter(status=TicketStatus.OPEN).count()
    unassigned_tickets = SupportTicket.objects.filter(
        status=TicketStatus.OPEN, assigned_to=None
    ).count()

    one_hour_ago = timezone.now() - timedelta(hours=1)
    transactions_last_hour = Transaction.objects.filter(
        occurred_at__gte=one_hour_ago,
        status=TransactionStatus.COMPLETED,
    ).count()

    return {
        "pending_kyc_users":       pending_kyc_users,
        "pending_kyc_docs":        pending_kyc_docs,
        "open_support_tickets":    open_tickets,
        "unassigned_tickets":      unassigned_tickets,
        "transactions_last_hour":  transactions_last_hour,
    }


# ---------------------------------------------------------------------------
# Time-series: transaction volume
# ---------------------------------------------------------------------------

def get_daily_transaction_volume(*, days: int = 7) -> list:
    """
    Volume and count per calendar day for the last `days` days.
    Returns: [{day, count, volume}]
    """
    from apps.ledger.constants import TransactionStatus
    from apps.ledger.models import Transaction

    since = timezone.now() - timedelta(days=days)
    return list(
        Transaction.objects
        .filter(status=TransactionStatus.COMPLETED, occurred_at__gte=since)
        .annotate(day=TruncDay("occurred_at"))
        .values("day")
        .annotate(count=Count("id"), volume=Sum("amount"))
        .order_by("day")
    )


def get_weekly_transaction_volume(*, weeks: int = 4) -> list:
    """
    Volume and count per ISO week for the last `weeks` weeks.
    Returns: [{week, count, volume}]
    """
    from apps.ledger.constants import TransactionStatus
    from apps.ledger.models import Transaction

    since = timezone.now() - timedelta(weeks=weeks)
    return list(
        Transaction.objects
        .filter(status=TransactionStatus.COMPLETED, occurred_at__gte=since)
        .annotate(week=TruncWeek("occurred_at"))
        .values("week")
        .annotate(count=Count("id"), volume=Sum("amount"))
        .order_by("week")
    )


def get_volume_by_transaction_type(*, days: int = 30) -> list:
    """
    Transaction count and volume broken down by type for the last `days` days.
    """
    from apps.ledger.constants import TransactionStatus
    from apps.ledger.models import Transaction

    since = timezone.now() - timedelta(days=days)
    return list(
        Transaction.objects
        .filter(status=TransactionStatus.COMPLETED, occurred_at__gte=since)
        .values("transaction_type")
        .annotate(count=Count("id"), volume=Sum("amount"))
        .order_by("transaction_type")
    )


# ---------------------------------------------------------------------------
# Fee aggregation
# ---------------------------------------------------------------------------

def get_fee_aggregation(*, days: int = 30) -> dict:
    """
    Fee revenue breakdown by transaction type for the last `days` days.
    """
    from apps.ledger.constants import EntryType, TransactionStatus
    from apps.ledger.models import TransactionEntry

    since = timezone.now() - timedelta(days=days)
    by_type = list(
        TransactionEntry.objects
        .filter(
            entry_type=EntryType.FEE,
            transaction__status=TransactionStatus.COMPLETED,
            created_at__gte=since,
        )
        .values("transaction__transaction_type")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("transaction__transaction_type")
    )

    total = TransactionEntry.objects.filter(
        entry_type=EntryType.FEE,
        transaction__status=TransactionStatus.COMPLETED,
        created_at__gte=since,
    ).aggregate(total=Sum("amount"))

    return {
        "period_days":          days,
        "by_transaction_type":  by_type,
        "total_fee_revenue":    total["total"] or Decimal("0"),
    }


# ---------------------------------------------------------------------------
# User growth
# ---------------------------------------------------------------------------

def get_user_growth(*, days: int = 30) -> list:
    """
    New user registrations per day for the last `days` days.
    Returns: [{day, new_users}]
    """
    from apps.users.models import User

    since = timezone.now() - timedelta(days=days)
    return list(
        User.objects
        .filter(created_at__gte=since)
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(new_users=Count("id"))
        .order_by("day")
    )


def get_user_status_breakdown() -> dict:
    """Count of users in each status."""
    from apps.users.constants import UserStatus
    from apps.users.models import User

    return {
        status: User.objects.filter(status=status).count()
        for status, _ in UserStatus.CHOICES
    }


# ---------------------------------------------------------------------------
# Audit: transaction trace
# ---------------------------------------------------------------------------

def get_transaction_trace(reference_number: str) -> dict:
    """
    Full audit trace for a single transaction:
      - Transaction + metadata
      - All double-entry ledger entries with account info
      - TransactionHistory snapshot
      - Child reversals
      - FraudAlerts triggered by this transaction
    """
    from apps.ledger.models import Transaction, TransactionEntry, TransactionHistory
    from apps.risk.models import FraudAlert

    tx = (
        Transaction.objects
        .select_related("currency", "customer", "initiated_by", "parent_transaction__currency")
        .get(reference_number=reference_number)
    )

    entries = list(
        TransactionEntry.objects
        .filter(transaction=tx)
        .select_related("account", "account__user", "account__currency")
        .order_by("sequence_no")
    )

    history = None
    try:
        history = TransactionHistory.objects.get(transaction=tx)
    except TransactionHistory.DoesNotExist:
        pass

    reversals = list(
        Transaction.objects
        .filter(parent_transaction=tx)
        .values("reference_number", "status", "amount", "occurred_at")
    )

    fraud_alerts = list(
        FraudAlert.objects
        .filter(transaction=tx)
        .values("id", "severity", "status", "risk_score", "auto_action_taken", "created_at")
    )

    return {
        "transaction":  tx,
        "entries":      entries,
        "history":      history,
        "reversals":    reversals,
        "fraud_alerts": fraud_alerts,
    }


# ---------------------------------------------------------------------------
# Audit: account restriction history
# ---------------------------------------------------------------------------

def get_account_restriction_history(account_id: int):
    """All FREEZE / BLOCK events for an account, newest first."""
    from apps.accounts.models import AccountRestriction

    return (
        AccountRestriction.objects
        .filter(account_id=account_id)
        .select_related("applied_by", "released_by")
        .order_by("-starts_at")
    )


# ---------------------------------------------------------------------------
# Audit: fraud decision history
# ---------------------------------------------------------------------------

def get_alert_decision_history(alert_id: int | None = None):
    """
    Decision history for a single alert (when alert_id given) or all alerts.
    """
    from apps.risk.models import FraudDecision

    qs = FraudDecision.objects.select_related(
        "alert", "officer"
    ).order_by("-executed_at")
    if alert_id is not None:
        qs = qs.filter(alert_id=alert_id)
    return qs


# ---------------------------------------------------------------------------
# Recent activity (Operations view)
# ---------------------------------------------------------------------------

def get_recent_transactions(*, limit: int = 50):
    """Most recent COMPLETED transactions for the operations view."""
    from apps.ledger.constants import TransactionStatus
    from apps.ledger.models import Transaction

    return (
        Transaction.objects
        .filter(status=TransactionStatus.COMPLETED)
        .select_related("currency", "customer")
        .order_by("-occurred_at")[:limit]
    )
