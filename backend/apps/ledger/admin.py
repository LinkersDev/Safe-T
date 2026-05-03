"""Django admin registrations for ledger models."""
from django.contrib import admin

from .models import FeeRule, Transaction, TransactionEntry, TransactionHistory


class TransactionEntryInline(admin.TabularInline):
    model = TransactionEntry
    extra = 0
    readonly_fields = ("entry_type", "amount", "sequence_no", "account", "created_at")
    can_delete = False


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "reference_number",
        "transaction_type",
        "status",
        "amount",
        "currency",
        "customer",
        "channel",
        "occurred_at",
        "completed_at",
    )
    list_filter = ("transaction_type", "status", "channel", "currency")
    search_fields = ("reference_number", "idempotency_key", "customer__phone_number")
    readonly_fields = (
        "reference_number",
        "transaction_type",
        "status",
        "amount",
        "currency",
        "customer",
        "initiated_by",
        "parent_transaction",
        "idempotency_key",
        "occurred_at",
        "completed_at",
        "reversed_at",
        "failure_code",
        "failure_reason",
        "metadata_json",
        "risk_score",
        "otp_verified_at",
    )
    inlines = [TransactionEntryInline]
    date_hierarchy = "occurred_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TransactionEntry)
class TransactionEntryAdmin(admin.ModelAdmin):
    list_display = ("transaction", "entry_type", "amount", "account", "sequence_no", "created_at")
    list_filter = ("entry_type",)
    readonly_fields = ("transaction", "account", "entry_type", "amount", "sequence_no", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TransactionHistory)
class TransactionHistoryAdmin(admin.ModelAdmin):
    list_display = ("reference_number", "transaction_type", "status", "amount", "currency_code", "archived_at")
    readonly_fields = (
        "transaction",
        "reference_number",
        "transaction_type",
        "status",
        "currency_code",
        "amount",
        "payload_json",
        "archived_at",
    )
    search_fields = ("reference_number",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(FeeRule)
class FeeRuleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "transaction_type",
        "currency",
        "fixed_fee",
        "percentage_fee",
        "priority",
        "is_active",
        "effective_from",
        "effective_to",
    )
    list_filter = ("transaction_type", "is_active", "currency")
    search_fields = ("name",)
