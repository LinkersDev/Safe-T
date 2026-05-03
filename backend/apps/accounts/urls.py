"""Customer-facing account endpoints."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.account_list, name="account-list"),
    path("<int:account_id>/", views.account_detail, name="account-detail"),
    path("<int:account_id>/transactions/", views.account_transactions, name="account-transactions"),
    path("beneficiaries/", views.beneficiary_list_create, name="beneficiary-list-create"),
    path("beneficiaries/<int:beneficiary_id>/", views.beneficiary_remove, name="beneficiary-remove"),
]
