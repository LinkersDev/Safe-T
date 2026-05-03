"""Read-only queries for the risk app."""
from .constants import AlertStatus
from .models import FraudAlert


def get_open_alerts():
    return (
        FraudAlert.objects
        .filter(status=AlertStatus.OPEN)
        .select_related("user", "account", "transaction", "reviewed_by")
        .order_by("-created_at")
    )


def get_alerts(*, status: str | None = None, severity: str | None = None):
    qs = FraudAlert.objects.select_related(
        "user", "account", "transaction", "reviewed_by"
    ).order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if severity:
        qs = qs.filter(severity=severity)
    return qs


def get_alert_by_id(alert_id: int) -> FraudAlert:
    return (
        FraudAlert.objects
        .select_related("user", "account", "transaction", "login_log", "reviewed_by")
        .prefetch_related("decision")
        .get(pk=alert_id)
    )
