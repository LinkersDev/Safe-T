"""DRF serializers for the ledger app."""
from decimal import Decimal

from rest_framework import serializers

from .constants import EntryType, TransactionType
from .models import FeeRule, Transaction, TransactionEntry, TransactionHistory


def _account_party_label(account) -> str | None:
    if account.user_id:
        return account.user.full_name
    name = (account.account_name or "").strip()
    return name or None


def _counterparty_display_for_customer(transaction: Transaction) -> str:
    """Human-readable counterparty for the customer-facing ledger list."""
    customer_id = transaction.customer_id
    if customer_id is None:
        return "—"

    ctype = transaction.transaction_type
    entries = list(transaction.entries.all())

    if ctype == TransactionType.DEPOSIT:
        if transaction.initiated_by_id:
            return f"From: {transaction.initiated_by.full_name}"
        return "From: Branch"

    if ctype == TransactionType.WITHDRAWAL:
        if transaction.initiated_by_id:
            return f"To: {transaction.initiated_by.full_name}"
        return "To: Branch"

    principal = Decimal(transaction.amount)

    if ctype == TransactionType.TRANSFER:
        outgoing = any(
            e.entry_type == EntryType.DEBIT
            and e.amount == principal
            and e.account.user_id == customer_id
            for e in entries
        )
        incoming = any(
            e.entry_type == EntryType.CREDIT
            and e.amount == principal
            and e.account.user_id == customer_id
            for e in entries
        )
        if outgoing:
            for e in entries:
                if (
                    e.entry_type == EntryType.CREDIT
                    and e.amount == principal
                    and e.account.user_id != customer_id
                ):
                    label = _account_party_label(e.account)
                    return f"To: {label}" if label else "To: —"
            return "To: —"
        if incoming:
            for e in entries:
                if (
                    e.entry_type == EntryType.DEBIT
                    and e.amount == principal
                    and e.account.user_id != customer_id
                ):
                    label = _account_party_label(e.account)
                    return f"From: {label}" if label else "From: —"
            return "From: —"
        return "—"

    if ctype in (TransactionType.QR_PAYMENT, TransactionType.BILL_PAYMENT):
        outgoing = any(
            e.entry_type == EntryType.DEBIT
            and e.amount == principal
            and e.account.user_id == customer_id
            for e in entries
        )
        if outgoing:
            for e in entries:
                if (
                    e.entry_type == EntryType.CREDIT
                    and e.amount == principal
                    and e.account.user_id != customer_id
                ):
                    label = _account_party_label(e.account)
                    return f"To: {label}" if label else "To: —"
            for e in entries:
                if e.entry_type == EntryType.CREDIT and e.amount == principal:
                    label = _account_party_label(e.account)
                    if label:
                        return f"To: {label}"
            return "To: —"
        return "—"

    return "—"


class TransactionEntrySerializer(serializers.ModelSerializer):
    account_id = serializers.IntegerField(source="account.id", read_only=True)
    account_number = serializers.CharField(source="account.account_number", read_only=True)
    account_owner_name = serializers.CharField(source="account.user.full_name", read_only=True, default=None)
    account_owner_phone = serializers.CharField(source="account.user.phone_number", read_only=True, default=None)

    class Meta:
        model = TransactionEntry
        fields = [
            "id",
            "entry_type",
            "amount",
            "sequence_no",
            "account_id",
            "account_number",
            "account_owner_name",
            "account_owner_phone",
            "created_at",
        ]


class TransactionSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source="currency_id", read_only=True)
    entries = TransactionEntrySerializer(many=True, read_only=True)
    teller_operation = serializers.SerializerMethodField()
    counterparty_display = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "reference_number",
            "transaction_type",
            "status",
            "currency_code",
            "amount",
            "description",
            "channel",
            "requires_otp",
            "risk_score",
            "occurred_at",
            "completed_at",
            "reversed_at",
            "failure_code",
            "failure_reason",
            "teller_operation",
            "counterparty_display",
            "entries",
        ]

    def get_counterparty_display(self, obj: Transaction) -> str:
        return _counterparty_display_for_customer(obj)

    def get_teller_operation(self, obj: Transaction):
        try:
            return (obj.metadata_json or {}).get("teller_operation")
        except Exception:
            return None


class TransactionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — no nested entries."""
    currency_code = serializers.CharField(source="currency_id", read_only=True)
    counterparty_display = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "reference_number",
            "transaction_type",
            "status",
            "currency_code",
            "amount",
            "description",
            "channel",
            "occurred_at",
            "completed_at",
            "counterparty_display",
        ]

    def get_counterparty_display(self, obj: Transaction) -> str:
        return _counterparty_display_for_customer(obj)


class ReverseTransactionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class FeeRuleSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source="currency_id", read_only=True)

    class Meta:
        model = FeeRule
        fields = [
            "id",
            "name",
            "transaction_type",
            "currency_code",
            "min_amount",
            "max_amount",
            "fixed_fee",
            "percentage_fee",
            "min_fee",
            "max_fee",
            "priority",
            "is_active",
            "effective_from",
            "effective_to",
        ]


class TransactionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionHistory
        fields = [
            "id",
            "reference_number",
            "transaction_type",
            "status",
            "currency_code",
            "amount",
            "payload_json",
            "archived_at",
        ]
