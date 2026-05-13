"""DRF serializers for the risk app."""
from rest_framework import serializers

from .constants import DecisionAction
from .models import FraudAlert, FraudDecision


class FraudDecisionSerializer(serializers.ModelSerializer):
    officer_name = serializers.CharField(source="officer.full_name", read_only=True, default=None)

    class Meta:
        model  = FraudDecision
        fields = ["id", "action", "notes", "officer_name", "executed_at"]
        read_only_fields = fields


class FraudAlertSerializer(serializers.ModelSerializer):
    user_phone  = serializers.CharField(source="user.phone_number", read_only=True, default=None)
    user_name   = serializers.CharField(source="user.full_name",    read_only=True, default=None)
    account_number = serializers.CharField(
        source="account.account_number", read_only=True, default=None
    )
    tx_reference = serializers.CharField(
        source="transaction.reference_number", read_only=True, default=None
    )
    transaction_type = serializers.CharField(
        source="transaction.transaction_type", read_only=True, default=None
    )
    transaction_amount = serializers.DecimalField(
        source="transaction.amount", max_digits=15, decimal_places=2, read_only=True, default=None
    )
    transaction_currency = serializers.CharField(
        source="transaction.currency_id", read_only=True, default=None
    )
    login_device_id = serializers.CharField(
        source="login_log.device_id", read_only=True, default=None
    )
    login_ip_address = serializers.CharField(
        source="login_log.ip_address", read_only=True, default=None
    )
    login_location = serializers.CharField(
        source="login_log.location_country", read_only=True, default=None
    )
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.full_name", read_only=True, default=None
    )
    decision = FraudDecisionSerializer(read_only=True)

    class Meta:
        model  = FraudAlert
        fields = [
            "id", "alert_type", "severity", "status", "risk_score",
            "ml_fraud_probability", "rule_based_score", "combined_score",
            "user_phone", "user_name", "account_number", "tx_reference",
            "transaction_type", "transaction_amount", "transaction_currency",
            "login_device_id", "login_ip_address", "login_location",
            "rules_triggered", "auto_action_taken",
            "reviewed_by_name", "reviewed_at",
            "decision",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class ReviewAlertSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=DecisionAction.CHOICES)
    notes  = serializers.CharField(required=False, allow_blank=True, default="")
