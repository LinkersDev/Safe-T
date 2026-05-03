"""Reporting URLs.  Prefix: /api/staff/reports/"""
from django.urls import path

from . import views

urlpatterns = [
    # ── Admin ─────────────────────────────────────────────────────────────
    path("admin/summary/",                     views.admin_summary,           name="report-admin-summary"),
    path("admin/users/growth/",                views.user_growth,             name="report-user-growth"),
    path("admin/users/status/",                views.user_status_breakdown,   name="report-user-status"),
    path("admin/transactions/volume/",         views.transaction_volume,      name="report-tx-volume"),
    path("admin/transactions/by-type/",        views.transaction_by_type,     name="report-tx-by-type"),
    path("admin/fees/aggregate/",              views.fee_aggregate,           name="report-fee-aggregate"),

    # ── Risk Officer ───────────────────────────────────────────────────────
    path("risk/summary/",                      views.risk_summary,            name="report-risk-summary"),
    path("risk/metrics/",                      views.fraud_metrics,           name="report-fraud-metrics"),

    # ── Operations ─────────────────────────────────────────────────────────
    path("operations/summary/",                views.operations_summary,      name="report-ops-summary"),
    path("operations/transactions/recent/",    views.recent_transactions,     name="report-recent-tx"),

    # ── Audit ──────────────────────────────────────────────────────────────
    path("audit/transactions/<str:reference_number>/trace/",  views.transaction_trace,           name="report-tx-trace"),
    path("audit/accounts/<int:account_id>/restrictions/",     views.account_restriction_history, name="report-account-restrictions"),
    path("audit/risk/alerts/<int:alert_id>/decisions/",       views.alert_decision_history,      name="report-alert-decisions"),
]
