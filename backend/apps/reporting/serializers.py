"""
Lightweight read-only serializers for reporting responses.

All serializers are read-only (no write path).
Where a selector returns raw dicts (aggregation results) the view
formats them inline — no serializer overhead needed.
"""
from rest_framework import serializers


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class AdminSummarySerializer(serializers.Serializer):
    total_users              = serializers.IntegerField()
    active_users             = serializers.IntegerField()
    pending_users            = serializers.IntegerField()
    blocked_users            = serializers.IntegerField()
    total_transaction_count  = serializers.IntegerField()
    total_transaction_volume = serializers.DecimalField(max_digits=22, decimal_places=2)
    total_available_balance  = serializers.DecimalField(max_digits=22, decimal_places=2)
    total_ledger_balance     = serializers.DecimalField(max_digits=22, decimal_places=2)
    fee_revenue              = serializers.DecimalField(max_digits=22, decimal_places=2)


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------

class RiskSummarySerializer(serializers.Serializer):
    open_alerts    = serializers.IntegerField()
    total_alerts   = serializers.IntegerField()
    by_severity    = serializers.DictField(child=serializers.IntegerField())
    by_type        = serializers.DictField(child=serializers.IntegerField())
    auto_actioned  = serializers.IntegerField()


class FraudMetricsSerializer(serializers.Serializer):
    period_days            = serializers.IntegerField()
    total_alerts           = serializers.IntegerField()
    critical_alerts        = serializers.IntegerField()
    auto_frozen_accounts   = serializers.IntegerField()
    resolved_alerts        = serializers.IntegerField()
    resolution_rate_pct    = serializers.FloatField()
    by_day                 = serializers.ListField(child=serializers.DictField())


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

class OperationsSummarySerializer(serializers.Serializer):
    pending_kyc_users      = serializers.IntegerField()
    pending_kyc_docs       = serializers.IntegerField()
    open_support_tickets   = serializers.IntegerField()
    unassigned_tickets     = serializers.IntegerField()
    transactions_last_hour = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Transaction trace (audit)
# ---------------------------------------------------------------------------

class TraceEntrySerializer(serializers.Serializer):
    id           = serializers.IntegerField()
    entry_type   = serializers.CharField()
    amount       = serializers.DecimalField(max_digits=22, decimal_places=2)
    sequence_no  = serializers.IntegerField()
    account_id   = serializers.IntegerField()
    account_number = serializers.CharField(source="account.account_number")
    account_user_phone = serializers.CharField(source="account.user.phone_number", default=None)
    created_at   = serializers.DateTimeField()


class TransactionTraceSerializer(serializers.Serializer):
    reference_number  = serializers.CharField(source="transaction.reference_number")
    transaction_type  = serializers.CharField(source="transaction.transaction_type")
    status            = serializers.CharField(source="transaction.status")
    amount            = serializers.DecimalField(source="transaction.amount", max_digits=22, decimal_places=2)
    currency          = serializers.CharField(source="transaction.currency.code")
    risk_score        = serializers.DecimalField(source="transaction.risk_score", max_digits=5, decimal_places=2, allow_null=True)
    occurred_at       = serializers.DateTimeField(source="transaction.occurred_at")
    completed_at      = serializers.DateTimeField(source="transaction.completed_at", allow_null=True)
    customer_phone    = serializers.CharField(source="transaction.customer.phone_number", default=None, allow_null=True)
    entries           = TraceEntrySerializer(many=True)
    reversals         = serializers.ListField(child=serializers.DictField())
    fraud_alerts      = serializers.ListField(child=serializers.DictField())
    has_history       = serializers.SerializerMethodField()

    def get_has_history(self, obj):
        return obj["history"] is not None


# ---------------------------------------------------------------------------
# Account restriction (audit)
# ---------------------------------------------------------------------------

class RestrictionHistorySerializer(serializers.Serializer):
    id               = serializers.IntegerField()
    restriction_type = serializers.CharField()
    reason           = serializers.CharField()
    source           = serializers.CharField()
    is_active        = serializers.BooleanField()
    applied_by_phone = serializers.CharField(source="applied_by.phone_number", default=None, allow_null=True)
    released_by_phone = serializers.CharField(source="released_by.phone_number", default=None, allow_null=True)
    starts_at        = serializers.DateTimeField()
    ends_at          = serializers.DateTimeField(allow_null=True)


# ---------------------------------------------------------------------------
# Recent transactions (Operations view)
# ---------------------------------------------------------------------------

class RecentTransactionSerializer(serializers.Serializer):
    reference_number  = serializers.CharField()
    transaction_type  = serializers.CharField()
    status            = serializers.CharField()
    amount            = serializers.DecimalField(max_digits=22, decimal_places=2)
    currency          = serializers.CharField(source="currency.code")
    customer_phone    = serializers.CharField(source="customer.phone_number", default=None, allow_null=True)
    occurred_at       = serializers.DateTimeField()
    risk_score        = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
