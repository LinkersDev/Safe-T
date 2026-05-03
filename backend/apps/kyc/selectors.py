"""Read-only queries for the KYC app."""
from apps.users.constants import KycStatus

from .models import KycDocument


def get_documents_for_user(user_id: int):
    """Return all KYC documents for a user, newest first."""
    return KycDocument.objects.filter(user_id=user_id).select_related("reviewed_by")


def get_pending_kyc_users():
    """Return users whose kyc_status is PENDING — the staff review queue."""
    from apps.users.models import User
    return (
        User.objects.filter(kyc_status=KycStatus.PENDING)
        .prefetch_related("kyc_documents")
        .order_by("id")
    )


def get_document_by_id(doc_id: int) -> KycDocument:
    return KycDocument.objects.select_related("user", "reviewed_by").get(pk=doc_id)
