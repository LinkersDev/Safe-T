"""Django admin registrations for the accounts app."""
from django.contrib import admin

from .models import Account, AccountRestriction, Beneficiary, Currency


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "symbol", "decimal_places", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    ordering = ["code"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = [
        "account_number",
        "account_name",
        "user",
        "currency",
        "status",
        "available_balance",
        "ledger_balance",
        "opened_at",
    ]
    list_filter = ["status", "currency"]
    search_fields = ["account_number", "account_name", "user__phone_number"]
    readonly_fields = [
        "account_number",
        "available_balance",
        "ledger_balance",
        "blocked_amount",
        "opened_at",
        "updated_at",
    ]
    ordering = ["-opened_at"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AccountRestriction)
class AccountRestrictionAdmin(admin.ModelAdmin):
    list_display = [
        "account",
        "restriction_type",
        "source",
        "is_active",
        "applied_by",
        "starts_at",
        "ends_at",
    ]
    list_filter = ["restriction_type", "is_active", "source"]
    search_fields = ["account__account_number"]
    readonly_fields = ["starts_at", "created_at"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ["owner", "destination_account", "nickname", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["owner__phone_number", "nickname"]
    ordering = ["-created_at"]
