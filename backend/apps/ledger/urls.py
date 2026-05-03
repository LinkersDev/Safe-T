"""Customer-facing ledger URL patterns (prefix: /api/ledger/)."""
from django.urls import path

from . import views

urlpatterns = [
    path("transactions/", views.transaction_list, name="ledger-transaction-list"),
    path("transactions/<str:reference_number>/", views.transaction_detail, name="ledger-transaction-detail"),
]
