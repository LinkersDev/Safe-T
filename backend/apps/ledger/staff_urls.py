"""Staff-facing ledger URL patterns (prefix: /api/staff/ledger/)."""
from django.urls import path

from . import views

urlpatterns = [
    path("transactions/", views.staff_transaction_list, name="staff-ledger-transaction-list"),
    path("transactions/<str:reference_number>/", views.staff_transaction_detail, name="staff-ledger-transaction-detail"),
    path("transactions/<str:reference_number>/reverse/", views.reverse_transaction_view, name="staff-ledger-reverse"),
    path("transactions/<str:reference_number>/archive/", views.archive_transaction_view, name="staff-ledger-archive"),
    path("fee-rules/", views.fee_rule_list, name="staff-ledger-fee-rules"),
]
