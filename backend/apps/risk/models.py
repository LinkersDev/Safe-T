"""Risk engine models: FraudAlert, FraudDecision."""
from django.conf import settings
from django.db import models

from .constants import AlertSeverity, AlertStatus, AlertType, DecisionAction


class FraudAlert(models.Model):
    """
    Created whenever the scoring engine detects suspicious activity.

    Detection lifecycle:
      OPEN → REVIEWED / DISMISSED / ACTIONED

    Sources:
      - Transaction scoring (on_commit after post_transaction)
      - Login scoring (synchronous, after LoginLog is written)

    For CRITICAL transaction alerts the engine auto-freezes the source
    account and records "ACCOUNT_AUTO_FROZEN" in auto_action_taken.
    """
    alert_type = models.CharField(max_length=20, choices=AlertType.CHOICES, db_index=True)
    severity   = models.CharField(max_length=20, choices=AlertSeverity.CHOICES, db_index=True)
    status     = models.CharField(
        max_length=20, choices=AlertStatus.CHOICES, default=AlertStatus.OPEN, db_index=True
    )
    risk_score = models.DecimalField(max_digits=5, decimal_places=2)

    # User who triggered the alert
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="fraud_alerts",
    )
    # Affected account (populated for transaction alerts; null for login alerts)
    account = models.ForeignKey(
        "accounts.Account",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="fraud_alerts",
    )
    # Event that triggered this alert
    transaction = models.ForeignKey(
        "ledger.Transaction",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="fraud_alerts",
    )
    login_log = models.ForeignKey(
        "security.LoginLog",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="fraud_alerts",
    )

    # Human-readable list of rules that fired (e.g. ["Large transaction: USD 10000"])
    rules_triggered = models.JSONField(default=list)

    # Records any automatic action taken by the engine
    auto_action_taken = models.CharField(max_length=50, blank=True)

    # Risk Officer review fields
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_fraud_alerts",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fraud_alerts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "severity"], name="fraud_alert_status_sev_idx"),
            models.Index(fields=["user", "created_at"],  name="fraud_alert_user_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"FraudAlert#{self.pk} [{self.severity}/{self.status}] "
            f"score={self.risk_score} type={self.alert_type}"
        )


class FraudDecision(models.Model):
    """
    Risk Officer's decision on a FraudAlert.

    One decision per alert (OneToOneField).  Creating a FraudDecision
    closes the alert (status → REVIEWED / DISMISSED / ACTIONED).
    """
    alert = models.OneToOneField(
        FraudAlert,
        on_delete=models.CASCADE,
        related_name="decision",
    )
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fraud_decisions",
    )
    action  = models.CharField(max_length=30, choices=DecisionAction.CHOICES)
    notes   = models.TextField(blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fraud_decisions"

    def __str__(self) -> str:
        return f"Decision#{self.pk} alert={self.alert_id} action={self.action}"
