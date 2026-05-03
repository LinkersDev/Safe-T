"""
Risk scoring rules.

All functions are pure in intent: they only read from the database and return
numeric scores + human-readable reason strings.  They do NOT write to the DB,
create alerts, or take account actions — that is the responsibility of services.py.

Public API:
  compute_transaction_score(tx_pk)  → (score: int, reasons: list[str], source_account_pk | None)
  compute_login_score(login_log_pk) → (score: int, reasons: list[str])
"""
import logging
from datetime import timedelta
from decimal import Decimal
from typing import NamedTuple

from django.utils import timezone

from .constants import ScoringConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class RuleHit(NamedTuple):
    points: int
    reason: str


def _is_abnormal_hour(dt) -> bool:
    """Return True if the hour (UTC) is between ABNORMAL_HOUR_START and END inclusive."""
    h = dt.hour
    return ScoringConfig.ABNORMAL_HOUR_START <= h <= ScoringConfig.ABNORMAL_HOUR_END


# ---------------------------------------------------------------------------
# Transaction rules
# ---------------------------------------------------------------------------

def _rule_amount(amount: Decimal) -> list[RuleHit]:
    if amount >= ScoringConfig.AMOUNT_CRITICAL_THRESHOLD:
        return [RuleHit(
            ScoringConfig.AMOUNT_CRITICAL_SCORE,
            f"Very large transaction: {amount}",
        )]
    if amount >= ScoringConfig.AMOUNT_HIGH_THRESHOLD:
        return [RuleHit(
            ScoringConfig.AMOUNT_HIGH_SCORE,
            f"High-value transaction: {amount}",
        )]
    return []


def _rule_velocity(source_account_pk: int, exclude_tx_pk: int) -> list[RuleHit]:
    """Count recent debits from the source account in the rolling window."""
    from apps.ledger.models import TransactionEntry
    from apps.ledger.constants import EntryType

    since = timezone.now() - timedelta(hours=ScoringConfig.VELOCITY_WINDOW_HOURS)
    count = (
        TransactionEntry.objects
        .filter(
            account_id=source_account_pk,
            entry_type=EntryType.DEBIT,
            created_at__gte=since,
        )
        .exclude(transaction_id=exclude_tx_pk)
        .count()
    )

    if count >= ScoringConfig.VELOCITY_COUNT_HIGH:
        return [RuleHit(
            ScoringConfig.VELOCITY_SCORE_HIGH,
            f"High velocity: {count} debits in last {ScoringConfig.VELOCITY_WINDOW_HOURS}h",
        )]
    if count >= ScoringConfig.VELOCITY_COUNT_MEDIUM:
        return [RuleHit(
            ScoringConfig.VELOCITY_SCORE_MEDIUM,
            f"Moderate velocity: {count} debits in last {ScoringConfig.VELOCITY_WINDOW_HOURS}h",
        )]
    return []


def _rule_abnormal_hour_tx(occurred_at) -> list[RuleHit]:
    if _is_abnormal_hour(occurred_at):
        return [RuleHit(
            ScoringConfig.ABNORMAL_HOUR_TX_SCORE,
            f"Transaction at abnormal hour: {occurred_at.hour:02d}:xx UTC",
        )]
    return []


def compute_transaction_score(tx_pk: int) -> tuple[int, list[str], int | None]:
    """
    Evaluate all transaction rules.

    Returns:
        (total_score, [reason_string, ...], source_account_pk_or_None)
    """
    from apps.ledger.models import Transaction, TransactionEntry
    from apps.ledger.constants import EntryType

    try:
        tx = Transaction.objects.select_related("currency").get(pk=tx_pk)
    except Transaction.DoesNotExist:
        logger.warning("compute_transaction_score: tx %s not found", tx_pk)
        return 0, [], None

    entries = list(
        TransactionEntry.objects
        .filter(transaction=tx)
        .order_by("sequence_no")
    )

    # Source account = first DEBIT entry (seq 1)
    source_account_pk = None
    for e in entries:
        if e.entry_type == EntryType.DEBIT and e.sequence_no == 1:
            source_account_pk = e.account_id
            break

    hits: list[RuleHit] = []
    hits.extend(_rule_amount(tx.amount))
    if source_account_pk:
        hits.extend(_rule_velocity(source_account_pk, tx.pk))
    hits.extend(_rule_abnormal_hour_tx(tx.occurred_at))

    score   = sum(h.points for h in hits)
    reasons = [h.reason for h in hits]

    logger.debug("TX score | tx=%s score=%s reasons=%s", tx_pk, score, reasons)
    return score, reasons, source_account_pk


# ---------------------------------------------------------------------------
# Login rules
# ---------------------------------------------------------------------------

def _rule_recent_failures(phone: str, exclude_pk: int) -> list[RuleHit]:
    from apps.security.models import LoginLog
    from apps.security.constants import LoginStatus

    since = timezone.now() - timedelta(minutes=ScoringConfig.FAILED_LOGIN_WINDOW_MIN)
    count = (
        LoginLog.objects
        .filter(phone_number=phone, status=LoginStatus.FAILED, attempted_at__gte=since)
        .exclude(pk=exclude_pk)
        .count()
    )

    if count >= ScoringConfig.FAILED_LOGIN_HIGH_COUNT:
        return [RuleHit(
            ScoringConfig.FAILED_LOGIN_HIGH_SCORE,
            f"Multiple failed logins: {count} in last {ScoringConfig.FAILED_LOGIN_WINDOW_MIN}min",
        )]
    if count >= ScoringConfig.FAILED_LOGIN_LOW_COUNT:
        return [RuleHit(
            ScoringConfig.FAILED_LOGIN_LOW_SCORE,
            f"Recent failed login: {count} in last {ScoringConfig.FAILED_LOGIN_WINDOW_MIN}min",
        )]
    return []


def _rule_new_device(user_pk: int, device_id: str) -> list[RuleHit]:
    if not device_id:
        return []
    from apps.security.models import UserDevice
    known = UserDevice.objects.filter(user_id=user_pk, device_uuid=device_id).exists()
    if not known:
        return [RuleHit(
            ScoringConfig.NEW_DEVICE_SCORE,
            f"Unrecognised device: {device_id[:20]}",
        )]
    return []


def _rule_new_country(user_pk: int, country: str, exclude_pk: int) -> list[RuleHit]:
    if not country:
        return []
    from apps.security.models import LoginLog
    from apps.security.constants import LoginStatus

    known = (
        LoginLog.objects
        .filter(user_id=user_pk, status=LoginStatus.SUCCESS)
        .exclude(pk=exclude_pk)
        .values_list("location_country", flat=True)
        .distinct()
    )
    if country not in list(known):
        return [RuleHit(
            ScoringConfig.NEW_COUNTRY_SCORE,
            f"Login from new country: {country}",
        )]
    return []


def _rule_abnormal_hour_login(attempted_at) -> list[RuleHit]:
    if _is_abnormal_hour(attempted_at):
        return [RuleHit(
            ScoringConfig.ABNORMAL_HOUR_LOGIN_SCORE,
            f"Login at abnormal hour: {attempted_at.hour:02d}:xx UTC",
        )]
    return []


def compute_login_score(login_log_pk: int) -> tuple[int, list[str]]:
    """
    Evaluate all login rules.

    Returns:
        (total_score, [reason_string, ...])
    """
    from apps.security.models import LoginLog

    try:
        log = LoginLog.objects.select_related("user").get(pk=login_log_pk)
    except LoginLog.DoesNotExist:
        logger.warning("compute_login_score: login_log %s not found", login_log_pk)
        return 0, []

    hits: list[RuleHit] = []
    hits.extend(_rule_recent_failures(log.phone_number, log.pk))

    if log.user_id:
        if log.device_id:
            hits.extend(_rule_new_device(log.user_id, log.device_id))
        if log.location_country:
            hits.extend(_rule_new_country(log.user_id, log.location_country, log.pk))

    hits.extend(_rule_abnormal_hour_login(log.attempted_at))

    score   = sum(h.points for h in hits)
    reasons = [h.reason for h in hits]

    logger.debug("Login score | log=%s score=%s reasons=%s", login_log_pk, score, reasons)
    return score, reasons
