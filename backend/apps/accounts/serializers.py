"""
Accounts app serializers.
"""
from __future__ import annotations

from rest_framework import serializers

from .models import Account, Beneficiary, Currency


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["code", "name", "symbol", "decimal_places"]


class AccountSerializer(serializers.ModelSerializer):
    currency = CurrencySerializer(read_only=True)
    owner_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Account
        fields = [
            "id",
            "account_number",
            "account_name",
            "status",
            "currency",
            "available_balance",
            "ledger_balance",
            "blocked_amount",
            "opened_at",
            "owner_name",
        ]
        read_only_fields = fields


class StaffAccountSerializer(AccountSerializer):
    """
    Staff view of an account includes owner metadata for rich account management UI.
    """

    owner_id = serializers.IntegerField(source="user.id", read_only=True)
    owner_phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    owner_status = serializers.CharField(source="user.status", read_only=True)
    owner_kyc_status = serializers.CharField(source="user.kyc_status", read_only=True)

    class Meta(AccountSerializer.Meta):
        fields = AccountSerializer.Meta.fields + [
            "owner_id",
            "owner_phone_number",
            "owner_status",
            "owner_kyc_status",
        ]


class BeneficiarySerializer(serializers.ModelSerializer):
    destination_account_number = serializers.CharField(
        source="destination_account.account_number",
        read_only=True,
    )
    destination_account_name = serializers.CharField(
        source="destination_account.account_name",
        read_only=True,
    )
    destination_currency = serializers.CharField(
        source="destination_account.currency.code",
        read_only=True,
    )

    class Meta:
        model = Beneficiary
        fields = [
            "id",
            "nickname",
            "destination_account_number",
            "destination_account_name",
            "destination_currency",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class AddBeneficiarySerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=34)
    nickname = serializers.CharField(max_length=100)

    def validate_account_number(self, value: str) -> str:
        from .validators import validate_account_number
        try:
            return validate_account_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class AccountRestrictionSerializer(serializers.Serializer):
    """Input for freeze / block operations."""
    reason = serializers.CharField(min_length=5, max_length=500)


class CloseAccountSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=5, max_length=500)
