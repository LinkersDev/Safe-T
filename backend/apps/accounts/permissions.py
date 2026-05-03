"""
Reusable DRF permission classes for the accounts app.
Most staff permission checks use HasPermission from users.permissions.
"""
from rest_framework.permissions import BasePermission

from apps.users.constants import UserStatus


class IsAccountOwner(BasePermission):
    """
    Object-level permission: allows access only if the authenticated user
    owns the account (used on account detail and transaction history views).
    """
    message = "You do not have access to this account."

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.pk
