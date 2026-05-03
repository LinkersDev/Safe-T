"""
Risk Officer API views.  All endpoints live under /api/staff/risk/.

GET  /api/staff/risk/alerts/           → list alerts (filter by status, severity)
GET  /api/staff/risk/alerts/{id}/      → alert detail + decision
POST /api/staff/risk/alerts/{id}/review/ → submit decision (action + notes)
POST /api/staff/risk/alerts/{id}/dismiss/ → shortcut dismiss
"""
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import HasPermission

from .exceptions import AlertAlreadyReviewedError, AlertNotFoundError
from .models import FraudAlert
from .selectors import get_alert_by_id, get_alerts
from .serializers import FraudAlertSerializer, ReviewAlertSerializer
from .services import dismiss_alert, review_alert

logger = logging.getLogger(__name__)


def _require_risk_perm(request):
    if not HasPermission.user_has_perm(request.user, "review_fraud_alert"):
        return Response(
            {"detail": "You do not have permission to review fraud alerts."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alert_list(request):
    """List fraud alerts.  Query params: ?status=OPEN&severity=CRITICAL"""
    err = _require_risk_perm(request)
    if err:
        return err
    filter_status   = request.query_params.get("status")
    filter_severity = request.query_params.get("severity")
    alerts = get_alerts(status=filter_status, severity=filter_severity)
    return Response(FraudAlertSerializer(alerts, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alert_detail(request, alert_id: int):
    """Return a single alert with its decision (if any)."""
    err = _require_risk_perm(request)
    if err:
        return err
    try:
        alert = get_alert_by_id(alert_id)
    except FraudAlert.DoesNotExist:
        return Response({"detail": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(FraudAlertSerializer(alert).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def alert_review(request, alert_id: int):
    """
    Risk Officer submits a decision on a fraud alert.

    Body: { "action": "FREEZE_ACCOUNT" | "BLOCK_ACCOUNT" | "DISMISS" | "WARN" | "ESCALATE",
            "notes": "optional text" }
    """
    err = _require_risk_perm(request)
    if err:
        return err

    ser = ReviewAlertSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        decision = review_alert(
            alert_id=alert_id,
            officer=request.user,
            action=ser.validated_data["action"],
            notes=ser.validated_data.get("notes", ""),
        )
    except AlertNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except AlertAlreadyReviewedError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    alert = get_alert_by_id(alert_id)
    return Response(FraudAlertSerializer(alert).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def alert_dismiss(request, alert_id: int):
    """Shorthand: dismiss an alert without requiring an action payload."""
    err = _require_risk_perm(request)
    if err:
        return err
    try:
        dismiss_alert(alert_id=alert_id, officer=request.user)
    except AlertNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except AlertAlreadyReviewedError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    alert = get_alert_by_id(alert_id)
    return Response(FraudAlertSerializer(alert).data)
