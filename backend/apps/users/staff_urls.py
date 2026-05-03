"""Staff-facing user management endpoints."""
from django.urls import path

from . import views
from apps.security.views import unlock_user_view

urlpatterns = [
    path("users/", views.users_list, name="staff-users-list"),
    path("users/pending/", views.pending_users_list, name="staff-users-pending"),
    path("users/staff/register/", views.register_staff_user, name="staff-users-staff-register"),
    path("users/<int:pk>/approve/", views.approve_user_view, name="staff-users-approve"),
    path("users/<int:pk>/reject/", views.reject_user_view, name="staff-users-reject"),
    path("users/<int:user_id>/unlock/", unlock_user_view, name="staff-users-unlock"),
]
