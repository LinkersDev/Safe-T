from django.contrib import admin

from .models import FraudAlert, FraudDecision


class FraudDecisionInline(admin.StackedInline):
    model = FraudDecision
    extra = 0
    readonly_fields = ("officer", "action", "notes", "executed_at")
    can_delete = False


@admin.register(FraudAlert)
class FraudAlertAdmin(admin.ModelAdmin):
    list_display   = ("id", "alert_type", "severity", "status", "risk_score", "ml_fraud_probability", "rule_based_score", "combined_score", "user", "created_at")
    list_filter    = ("severity", "status", "alert_type")
    search_fields  = ("user__phone_number", "user__full_name")
    readonly_fields = ("created_at", "updated_at", "reviewed_at", "auto_action_taken", "rules_triggered", "ml_fraud_probability", "rule_based_score", "combined_score")
    inlines        = [FraudDecisionInline]
    ordering       = ("-created_at",)


@admin.register(FraudDecision)
class FraudDecisionAdmin(admin.ModelAdmin):
    list_display  = ("id", "alert", "action", "officer", "executed_at")
    list_filter   = ("action",)
    readonly_fields = ("executed_at",)
