"""
Reusable DRF permission classes for the users app.
"""
from rest_framework.permissions import BasePermission

from .constants import RoleCode, UserStatus


class IsActiveUser(BasePermission):
    """Allows access only to users with ACTIVE status."""

    message = "Your account is not active."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.status == UserStatus.ACTIVE
        )


class IsAdminRole(BasePermission):
    message = "Admin role required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role
            and request.user.role.code == RoleCode.ADMIN
        )


class IsTellerOrAdmin(BasePermission):
    message = "Teller or Admin role required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role
            and request.user.role.code in {RoleCode.TELLER, RoleCode.ADMIN}
        )


class IsRiskOfficer(BasePermission):
    message = "Risk Officer role required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role
            and request.user.role.code == RoleCode.RISK_OFFICER
        )


class IsCustomerService(BasePermission):
    message = "Customer Service role required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role
            and request.user.role.code == RoleCode.CUSTOMER_SERVICE
        )


class IsStaffUser(BasePermission):
    """Any staff role."""
    message = "Staff access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role
            and request.user.role.is_staff_role
        )


class IsNotPending(BasePermission):
    """
    Blocks PENDING_VERIFICATION users from accessing financial endpoints.
    Used as a permission class on all ledger/payment views.
    """
    message = "Your account is pending staff verification. Transactions are not available yet."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.status == UserStatus.ACTIVE
        )


class HasPermission(BasePermission):
    """
    Checks that the authenticated user's role has a specific permission code.
    Usage in views:
        permission_classes = [IsAuthenticated, HasPermission]
        required_permission = "some_perm_code"

    Also usable as a static helper: HasPermission.user_has_perm(user, "perm_code")
    """
    required_permission: str = ""

    def has_permission(self, request, view):
        perm_code = getattr(view, "required_permission", self.required_permission)
        return self.user_has_perm(request.user, perm_code)

    @staticmethod
    def user_has_perm(user, perm_code: str) -> bool:
        if not user or not user.is_authenticated or not user.role:
            return False
        return user.role.role_permissions.filter(
            permission__code=perm_code
        ).exists()
