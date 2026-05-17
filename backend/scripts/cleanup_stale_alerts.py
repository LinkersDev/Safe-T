"""
Delete stale login alerts with score=0 but severity=MEDIUM.
These are inconsistent — current code would never create them.

Usage:
    python manage.py shell < scripts/cleanup_stale_alerts.py
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.risk.models import FraudAlert
from apps.risk.constants import AlertType, AlertSeverity

# Find login alerts with score 0 but severity MEDIUM (inconsistent data)
stale = FraudAlert.objects.filter(
    alert_type=AlertType.LOGIN,
    risk_score=0,
    severity=AlertSeverity.MEDIUM,
)

count = stale.count()
print(f"Found {count} stale login alerts (score=0 + severity=MEDIUM)")

if count > 0:
    stale.delete()
    print(f"Deleted {count} stale alerts.")
else:
    print("No stale alerts found.")

# Also report total remaining alerts
from apps.risk.constants import AlertStatus
total = FraudAlert.objects.count()
open_alerts = FraudAlert.objects.filter(status=AlertStatus.OPEN).count()
critical = FraudAlert.objects.filter(severity=AlertSeverity.CRITICAL).count()
high = FraudAlert.objects.filter(severity=AlertSeverity.HIGH).count()

print(f"\nRemaining: {total} total | {open_alerts} open | {critical} critical | {high} high")
