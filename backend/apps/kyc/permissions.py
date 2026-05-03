"""
DRF permission classes for KYC enforcement.

IsKYCApproved is applied to all endpoints that execute financial operations.
The same check is also enforced at the service layer (post_transaction) as
a defence-in-depth guard.
"""
from rest_framework.permissions import BasePermission

from apps.users.constants import KycStatus


class IsKYCApproved(BasePermission):
    """
    Allows access only to users whose KYC has been fully approved.

    Returns HTTP 403 with a descriptive message so the client can direct
    the user to the KYC upload flow.
    """

    message = (
        "Your identity verification (KYC) is not yet approved. "
        "Please upload your documents and wait for staff review."
    )

    def has_permission(self, request, view) -> bool:
        return (
            request.user is not None
            and request.user.is_authenticated
            and getattr(request.user, "kyc_status", None) == KycStatus.APPROVED
        )
