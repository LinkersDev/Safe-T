"""
Risk engine services.

Separation of concerns
────────────────────────────────────────────────
Detection  │ score_transaction / score_login
           │ Called via on_commit / after record_login
           │ Reads TX/login, runs rules, creates FraudAlert
───────────┼──────────────────────────────────────────────
Decision   │ review_alert / dismiss_alert
           │ Risk Officer submits action choice
           │ Creates FraudDecision, closes the alert
───────────┼──────────────────────────────────────────────
Action     │ _execute_action (internal)
           │ Calls accounts.services.freeze/block_account
           │ Does NOT modify the transaction or login records
────────────────────────────────────────────────

CRITICAL invariant: scoring failure must NEVER surface to the caller
or roll back a committed financial transaction.
"""
import logging

from django.utils import timezone

from .constants import AlertSeverity, AlertStatus, AlertType, DecisionAction
from .exceptions import AlertAlreadyReviewedError, AlertNotFoundError
from .models import FraudAlert, FraudDecision
from .rules import compute_login_score, compute_transaction_score

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _execute_action(alert: FraudAlert, action: str, actor=None) -> str:
    """
    Execute a physical account action.  Returns a description of what was done.
    Safe to call even when account is already in the target status.
    """
    from apps.accounts.services import block_account, freeze_account
    from apps.accounts.constants import RestrictionSource

    if action not in (DecisionAction.FREEZE_ACCOUNT, DecisionAction.BLOCK_ACCOUNT):
        return ""

    if not alert.account_id:
        return ""

    from apps.accounts.models import Account
    try:
        account = Account.objects.get(pk=alert.account_id)
    except Account.DoesNotExist:
        return ""

    reason = f"Risk engine: {action} triggered by FraudAlert#{alert.pk}"

    if action == DecisionAction.FREEZE_ACCOUNT:
        try:
            freeze_account(
                account=account,
                reason=reason,
                applied_by=actor,
                source=RestrictionSource.RISK_OFFICER,
            )
            return "ACCOUNT_FROZEN"
        except Exception as exc:
            logger.error("Auto-freeze failed | alert=%s err=%s", alert.pk, exc)
            return ""

    if action == DecisionAction.BLOCK_ACCOUNT:
        try:
            block_account(
                account=account,
                reason=reason,
                applied_by=actor,
                source=RestrictionSource.RISK_OFFICER,
            )
            return "ACCOUNT_BLOCKED"
        except Exception as exc:
            logger.error("Auto-block failed | alert=%s err=%s", alert.pk, exc)
            return ""

    return ""


# ---------------------------------------------------------------------------
# Detection — Transaction
# ---------------------------------------------------------------------------

def score_transaction(tx_pk: int) -> FraudAlert | None:
    """
    Score a committed transaction for fraud signals.

    Called via db_transaction.on_commit() from post_transaction().
    Swallows ALL exceptions — must not affect response time or atomicity.

    Workflow:
      1. Run rule engine → (score, reasons, source_account_pk)
      2. Update Transaction.risk_score
      3. If score < MEDIUM threshold → return None (low-risk, no alert)
      4. Create FraudAlert
      5. If severity == CRITICAL → auto-freeze source account
    """
    try:
        score, reasons, source_account_pk = compute_transaction_score(tx_pk)

        # Always update risk_score on the transaction (even for LOW)
        from apps.ledger.models import Transaction
        Transaction.objects.filter(pk=tx_pk).update(risk_score=score)

        severity = AlertSeverity.for_score(score)
        if severity == AlertSeverity.LOW:
            return None

        # Create the alert
        alert = FraudAlert.objects.create(
            alert_type=AlertType.TRANSACTION,
            severity=severity,
            status=AlertStatus.OPEN,
            risk_score=score,
            account_id=source_account_pk,
            transaction_id=tx_pk,
            rules_triggered=reasons,
        )

        # Populate user from the transaction
        try:
            tx = Transaction.objects.select_related("customer").get(pk=tx_pk)
            if tx.customer_id:
                alert.user = tx.customer
                alert.save(update_fields=["user"])
        except Exception:
            pass

        # CRITICAL → auto-freeze source account
        if severity == AlertSeverity.CRITICAL and source_account_pk:
            taken = _execute_action(alert, DecisionAction.FREEZE_ACCOUNT)
            if taken:
                alert.auto_action_taken = taken
                alert.status = AlertStatus.ACTIONED
                alert.save(update_fields=["auto_action_taken", "status", "updated_at"])

        logger.info(
            "FraudAlert created | alert=%s type=TRANSACTION tx=%s score=%s severity=%s",
            alert.pk, tx_pk, score, severity,
        )
        return alert

    except Exception as exc:
        logger.error(
            "score_transaction failed | tx_pk=%s error=%s", tx_pk, exc, exc_info=True
        )
        return None


# ---------------------------------------------------------------------------
# Detection — Login
# ---------------------------------------------------------------------------

def score_login(login_log_pk: int) -> FraudAlert | None:
    """
    Score a login event for fraud signals.

    Called synchronously from security.services.record_login() AFTER the
    LoginLog is committed, wrapped in try/except to avoid blocking the login.

    Workflow:
      1. Run rule engine → (score, reasons)
      2. Update LoginLog.risk_score
      3. If LOW → return None
      4. Create FraudAlert (no auto-freeze for login alerts)
    """
    try:
        score, reasons = compute_login_score(login_log_pk)

        from apps.security.models import LoginLog
        LoginLog.objects.filter(pk=login_log_pk).update(risk_score=score)

        severity = AlertSeverity.for_score(score)
        if severity == AlertSeverity.LOW:
            return None

        from apps.security.models import LoginLog as LLog
        log = LLog.objects.select_related("user").get(pk=login_log_pk)

        alert = FraudAlert.objects.create(
            alert_type=AlertType.LOGIN,
            severity=severity,
            status=AlertStatus.OPEN,
            risk_score=score,
            user=log.user,
            login_log_id=login_log_pk,
            rules_triggered=reasons,
        )

        logger.info(
            "FraudAlert created | alert=%s type=LOGIN log=%s score=%s severity=%s",
            alert.pk, login_log_pk, score, severity,
        )
        return alert

    except Exception as exc:
        logger.error(
            "score_login failed | login_log_pk=%s error=%s", login_log_pk, exc, exc_info=True
        )
        return None


# ---------------------------------------------------------------------------
# Decision — Risk Officer actions
# ---------------------------------------------------------------------------

def review_alert(
    *,
    alert_id: int,
    officer,
    action: str,
    notes: str = "",
) -> FraudDecision:
    """
    Record a Risk Officer's decision on an open alert.

    - Creates a FraudDecision.
    - Executes physical account action (FREEZE / BLOCK) if chosen.
    - Closes the alert with the appropriate status.
    """
    try:
        alert = FraudAlert.objects.get(pk=alert_id)
    except FraudAlert.DoesNotExist:
        raise AlertNotFoundError(f"FraudAlert {alert_id} not found.")

    if alert.status not in (AlertStatus.OPEN,):
        raise AlertAlreadyReviewedError(
            f"Alert {alert_id} is already {alert.status} and cannot be reviewed again."
        )

    decision = FraudDecision.objects.create(
        alert=alert,
        officer=officer,
        action=action,
        notes=notes,
    )

    # Execute physical action
    _execute_action(alert, action, actor=officer)

    # Close the alert
    if action == DecisionAction.DISMISS:
        final_status = AlertStatus.DISMISSED
    elif action in (DecisionAction.FREEZE_ACCOUNT, DecisionAction.BLOCK_ACCOUNT):
        final_status = AlertStatus.ACTIONED
    else:
        final_status = AlertStatus.REVIEWED

    alert.status      = final_status
    alert.reviewed_by = officer
    alert.reviewed_at = timezone.now()
    alert.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

    logger.info(
        "Alert reviewed | alert=%s officer=%s action=%s",
        alert_id, officer.pk if officer else None, action,
    )
    return decision


def dismiss_alert(*, alert_id: int, officer) -> FraudDecision:
    """Convenience shorthand for review_alert with action=DISMISS."""
    return review_alert(
        alert_id=alert_id,
        officer=officer,
        action=DecisionAction.DISMISS,
        notes="Dismissed — no action required.",
    )
