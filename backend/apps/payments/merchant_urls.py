"""Merchant-facing URL patterns (prefix: /api/merchant/)."""
from django.urls import path

from . import views

urlpatterns = [
    path("profile/", views.merchant_profile, name="merchant-profile"),
    path("qr/generate/", views.merchant_qr_generate, name="merchant-qr-generate"),
    path("qr/", views.merchant_qr_list, name="merchant-qr-list"),
    path("transactions/", views.merchant_transactions, name="merchant-transactions"),
]
