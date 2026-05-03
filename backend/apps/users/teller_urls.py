"""Teller-facing staff endpoints (prefix: /api/staff/teller/)."""

from django.urls import path

from . import teller_views


urlpatterns = [
    path("customers/register/", teller_views.register_customer_view, name="teller-register-customer"),
    path("customers/lookup/", teller_views.customer_lookup_view, name="teller-customer-lookup"),
    path("customers/<int:user_id>/profile/", teller_views.customer_profile_view, name="teller-customer-profile"),
    path("customers/<int:user_id>/kyc-profile/submit/", teller_views.customer_kyc_profile_submit_view, name="teller-customer-kyc-profile-submit"),
    path("customers/<int:user_id>/documents/upload/", teller_views.customer_kyc_document_upload_view, name="teller-customer-kyc-document-upload"),
    path("transactions/deposit/", teller_views.deposit_view, name="teller-deposit"),
    path("transactions/withdraw/", teller_views.withdraw_view, name="teller-withdraw"),
    path("accounts/<int:account_id>/transactions/", teller_views.account_transactions_view, name="teller-account-transactions"),
]

