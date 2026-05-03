"""
Ledger-specific DRF permission classes.

IsUserFullyActive — rejects PENDING_VERIFICATION users at the view layer.
This is a second line of defence; post_transaction also raises UserNotActiveError.
"""
from rest_framework.permissions import BasePermission

from apps.users.constants import UserStatus


class IsUserFullyActive(BasePermission):
    """
    Deny access to users whose status is PENDING_VERIFICATION.
    Intended for any view that can initiate or query monetary operations.
    """

    message = "Your account is not yet fully activated. Please complete verification."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return getattr(user, "status", None) != UserStatus.PENDING_VERIFICATION
