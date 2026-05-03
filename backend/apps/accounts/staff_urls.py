"""Staff-facing account management endpoints."""
from django.urls import path

from . import views

urlpatterns = [
    path("lookup/", views.staff_account_lookup, name="staff-account-lookup"),
    path("<int:account_id>/", views.staff_account_detail, name="staff-account-detail"),
    path("<int:account_id>/freeze/", views.freeze_account_view, name="staff-account-freeze"),
    path("<int:account_id>/unfreeze/", views.unfreeze_account_view, name="staff-account-unfreeze"),
    path("<int:account_id>/block/", views.block_account_view, name="staff-account-block"),
    path("<int:account_id>/unblock/", views.unblock_account_view, name="staff-account-unblock"),
    path("<int:account_id>/close/", views.close_account_view, name="staff-account-close"),
]
