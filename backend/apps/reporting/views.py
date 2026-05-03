"""
Reporting API views — all read-only, strict RBAC.

Endpoint map  (prefix: /api/staff/reports/)
───────────────────────────────────────────────────────────────────────
GET  admin/summary/                     → view_all_transactions
GET  admin/users/growth/?days=30        → view_all_users
GET  admin/users/status/                → view_all_users
GET  admin/transactions/volume/?...     → view_all_transactions
GET  admin/transactions/by-type/?days=  → view_all_transactions
GET  admin/fees/aggregate/?days=        → view_all_transactions
GET  risk/summary/                      → review_fraud_alert
GET  risk/metrics/?days=30              → review_fraud_alert
GET  operations/summary/                → review_kyc OR manage_support_tickets
GET  operations/transactions/recent/    → view_all_transactions
GET  audit/transactions/{ref}/trace/    → view_all_transactions
GET  audit/accounts/{id}/restrictions/  → view_all_accounts
GET  audit/risk/alerts/{id}/decisions/  → review_fraud_alert
───────────────────────────────────────────────────────────────────────

No business logic lives here — every view is a thin selector → serializer wrapper.
"""
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.ledger.models import Transaction
from apps.users.permissions import HasPermission

from .selectors import (
    get_account_restriction_history,
    get_admin_summary,
    get_alert_decision_history,
    get_daily_transaction_volume,
    get_fee_aggregation,
    get_fraud_metrics,
    get_operations_summary,
    get_recent_transactions,
    get_risk_summary,
    get_transaction_trace,
    get_user_growth,
    get_user_status_breakdown,
    get_volume_by_transaction_type,
    get_weekly_transaction_volume,
)
from .serializers import (
    AdminSummarySerializer,
    FraudMetricsSerializer,
    OperationsSummarySerializer,
    RecentTransactionSerializer,
    RestrictionHistorySerializer,
    RiskSummarySerializer,
    TransactionTraceSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------

def _require(request, *perms):
    """Return a 403 Response if the user lacks ANY of the listed permissions, else None."""
    for perm in perms:
        if not HasPermission.user_has_perm(request.user, perm):
            return Response(
                {"detail": f"Permission required: {perm}"},
                status=status.HTTP_403_FORBIDDEN,
            )
    return None


def _require_any(request, *perms):
    """Return a 403 Response if the user lacks ALL of the listed permissions, else None."""
    if any(HasPermission.user_has_perm(request.user, p) for p in perms):
        return None
    return Response(
        {"detail": f"One of these permissions required: {', '.join(perms)}"},
        status=status.HTTP_403_FORBIDDEN,
    )


def _parse_int_param(request, name: str, default: int, min_val: int = 1, max_val: int = 365) -> int:
    try:
        v = int(request.query_params.get(name, default))
        return max(min_val, min(max_val, v))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Admin — summary
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_summary(request):
    """Platform-wide financial and user snapshot."""
    err = _require(request, "view_all_transactions")
    if err:
        return err
    data = get_admin_summary()
    return Response(AdminSummarySerializer(data).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_growth(request):
    """New user registrations per day. ?days=30"""
    err = _require(request, "view_all_users")
    if err:
        return err
    days = _parse_int_param(request, "days", 30)
    rows = get_user_growth(days=days)
    return Response({"days": days, "rows": rows})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_status_breakdown(request):
    """Count of users in each status."""
    err = _require(request, "view_all_users")
    if err:
        return err
    return Response(get_user_status_breakdown())


# ---------------------------------------------------------------------------
# Admin — transactions
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transaction_volume(request):
    """
    Completed transaction volume.
    ?period=daily&days=7  (default)
    ?period=weekly&weeks=4
    """
    err = _require(request, "view_all_transactions")
    if err:
        return err

    period = request.query_params.get("period", "daily")
    if period == "weekly":
        weeks = _parse_int_param(request, "weeks", 4, max_val=52)
        rows  = get_weekly_transaction_volume(weeks=weeks)
        return Response({"period": "weekly", "weeks": weeks, "rows": rows})
    else:
        days = _parse_int_param(request, "days", 7)
        rows = get_daily_transaction_volume(days=days)
        return Response({"period": "daily", "days": days, "rows": rows})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transaction_by_type(request):
    """Volume and count broken down by transaction type. ?days=30"""
    err = _require(request, "view_all_transactions")
    if err:
        return err
    days = _parse_int_param(request, "days", 30)
    rows = get_volume_by_transaction_type(days=days)
    return Response({"days": days, "rows": rows})


# ---------------------------------------------------------------------------
# Admin — fees
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fee_aggregate(request):
    """Fee revenue by transaction type. ?days=30"""
    err = _require(request, "view_all_transactions")
    if err:
        return err
    days = _parse_int_param(request, "days", 30)
    return Response(get_fee_aggregation(days=days))


# ---------------------------------------------------------------------------
# Risk Officer dashboard
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def risk_summary(request):
    """Alert counts and severity breakdown for the Risk Officer."""
    err = _require(request, "review_fraud_alert")
    if err:
        return err
    return Response(RiskSummarySerializer(get_risk_summary()).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fraud_metrics(request):
    """Time-series fraud metrics. ?days=30"""
    err = _require(request, "review_fraud_alert")
    if err:
        return err
    days = _parse_int_param(request, "days", 30)
    return Response(FraudMetricsSerializer(get_fraud_metrics(days=days)).data)


# ---------------------------------------------------------------------------
# Operations dashboard (Teller / CustomerService)
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def operations_summary(request):
    """KYC + support + recent transaction snapshot for operations staff."""
    err = _require_any(request, "review_kyc", "manage_support_tickets")
    if err:
        return err
    return Response(OperationsSummarySerializer(get_operations_summary()).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recent_transactions(request):
    """50 most recent completed transactions for the ops view."""
    err = _require(request, "view_all_transactions")
    if err:
        return err
    limit = _parse_int_param(request, "limit", 50, max_val=200)
    txs = get_recent_transactions(limit=limit)
    return Response(RecentTransactionSerializer(txs, many=True).data)


# ---------------------------------------------------------------------------
# Audit views
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transaction_trace(request, reference_number: str):
    """
    Full audit trace for a single transaction:
    entries, history snapshot, reversals, and fraud alerts.
    """
    err = _require(request, "view_all_transactions")
    if err:
        return err
    try:
        trace = get_transaction_trace(reference_number)
    except Transaction.DoesNotExist:
        return Response(
            {"detail": f"Transaction '{reference_number}' not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(TransactionTraceSerializer(trace).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_restriction_history(request, account_id: int):
    """All FREEZE / BLOCK events on an account, newest first."""
    err = _require_any(request, "view_all_accounts", "freeze_account")
    if err:
        return err
    qs = get_account_restriction_history(account_id)
    return Response(RestrictionHistorySerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alert_decision_history(request, alert_id: int):
    """Decision history for a single fraud alert."""
    err = _require(request, "review_fraud_alert")
    if err:
        return err
    qs = get_alert_decision_history(alert_id=alert_id)
    results = [
        {
            "id":          d.pk,
            "action":      d.action,
            "notes":       d.notes,
            "officer":     d.officer.phone_number if d.officer else None,
            "executed_at": d.executed_at,
        }
        for d in qs
    ]
    return Response(results)
