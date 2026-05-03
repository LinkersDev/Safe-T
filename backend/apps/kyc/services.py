"""
KYC write-path services.

Rules:
  - upload_kyc_document   → creates document, advances kyc_status → PENDING
  - approve_user_kyc      → staff sets kyc_status = APPROVED
  - reject_user_kyc       → staff sets kyc_status = REJECTED
  - approve_kyc_document  → staff approves a single document
  - reject_kyc_document   → staff rejects a single document

The financial guard (_assert_kyc_approved) lives in apps.ledger.services
so that it sits as close as possible to post_transaction without creating
a circular import chain.
"""
import logging

from django.utils import timezone

from apps.users.constants import KycStatus

from .constants import KycDocumentStatus
from .exceptions import (
    KycAlreadyApprovedError,
    KycDocumentNotFoundError,
    KycIncompleteError,
    KycNotPendingError,
)
from .models import KycDocument

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Customer-facing
# ---------------------------------------------------------------------------

def upload_kyc_document(*, user, document_type: str, file) -> KycDocument:
    """
    Create a new KycDocument for *user* and advance their kyc_status
    to PENDING so staff know a review is needed.

    Calling this when kyc_status is already APPROVED does NOT downgrade it.
    A user re-uploading after a REJECTED review will transition back to PENDING.
    """
    doc = KycDocument.objects.create(
        user=user,
        document_type=document_type,
        file=file,
        status=KycDocumentStatus.PENDING,
    )

    # Advance to PENDING (unless already APPROVED)
    if user.kyc_status not in (KycStatus.APPROVED,):
        from apps.users.models import User
        User.objects.filter(pk=user.pk).update(kyc_status=KycStatus.PENDING)
        user.kyc_status = KycStatus.PENDING

    logger.info(
        "KYC document uploaded | user=%s type=%s doc_id=%s",
        user.pk,
        document_type,
        doc.pk,
    )
    return doc


# ---------------------------------------------------------------------------
# Staff-facing — user-level KYC status
# ---------------------------------------------------------------------------

def approve_user_kyc(*, user_id: int, reviewed_by) -> object:
    """
    Approve a user's KYC, granting them full financial access.
    Idempotent: calling on an already-APPROVED user raises KycAlreadyApprovedError.
    """
    from apps.users.models import User

    user = User.objects.get(pk=user_id)
    if user.kyc_status == KycStatus.APPROVED:
        raise KycAlreadyApprovedError(
            f"User {user_id} KYC is already APPROVED."
        )

    from .validators import validate_kyc_completeness
    completeness = validate_kyc_completeness(user_id=user_id)
    if not completeness.is_valid:
        raise KycIncompleteError(
            missing_fields=completeness.missing_fields,
            missing_documents=completeness.missing_documents,
        )

    User.objects.filter(pk=user_id).update(kyc_status=KycStatus.APPROVED)
    user.kyc_status = KycStatus.APPROVED

    logger.info(
        "KYC approved | user=%s reviewed_by=%s",
        user_id,
        reviewed_by.pk if reviewed_by else None,
    )
    return user


def reject_user_kyc(*, user_id: int, reviewed_by, reason: str = "") -> object:
    """
    Reject a user's KYC.  The user may re-upload documents to re-trigger
    a review (upload_kyc_document advances back to PENDING).
    """
    from apps.users.models import User

    user = User.objects.get(pk=user_id)
    if user.kyc_status not in (KycStatus.PENDING,):
        raise KycNotPendingError(
            f"Cannot reject KYC that is not PENDING (current: {user.kyc_status})."
        )

    User.objects.filter(pk=user_id).update(kyc_status=KycStatus.REJECTED)
    user.kyc_status = KycStatus.REJECTED

    logger.info(
        "KYC rejected | user=%s reviewed_by=%s reason=%s",
        user_id,
        reviewed_by.pk if reviewed_by else None,
        reason[:80] if reason else "",
    )
    return user


# ---------------------------------------------------------------------------
# Staff-facing — document-level review
# ---------------------------------------------------------------------------

def approve_kyc_document(*, doc_id: int, reviewed_by, notes: str = "") -> KycDocument:
    """Approve a single KYC document."""
    try:
        doc = KycDocument.objects.select_related("user").get(pk=doc_id)
    except KycDocument.DoesNotExist:
        raise KycDocumentNotFoundError(f"KycDocument {doc_id} not found.")

    doc.status = KycDocumentStatus.APPROVED
    doc.reviewed_by = reviewed_by
    doc.reviewed_at = timezone.now()
    doc.notes = notes
    doc.save(update_fields=["status", "reviewed_by", "reviewed_at", "notes", "updated_at"])

    logger.info("KYC document approved | doc=%s user=%s", doc_id, doc.user_id)
    return doc


def reject_kyc_document(
    *, doc_id: int, reviewed_by, reason: str, notes: str = ""
) -> KycDocument:
    """Reject a single KYC document with a mandatory rejection reason."""
    try:
        doc = KycDocument.objects.select_related("user").get(pk=doc_id)
    except KycDocument.DoesNotExist:
        raise KycDocumentNotFoundError(f"KycDocument {doc_id} not found.")

    doc.status = KycDocumentStatus.REJECTED
    doc.reviewed_by = reviewed_by
    doc.reviewed_at = timezone.now()
    doc.rejection_reason = reason
    doc.notes = notes
    doc.save(
        update_fields=[
            "status", "reviewed_by", "reviewed_at",
            "rejection_reason", "notes", "updated_at",
        ]
    )

    logger.info("KYC document rejected | doc=%s user=%s", doc_id, doc.user_id)
    return doc
