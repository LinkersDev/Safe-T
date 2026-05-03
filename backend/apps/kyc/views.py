"""
KYC API views.

Customer endpoints (prefix: /api/kyc/)
  GET  /api/kyc/status/            → current user's KYC status + documents
  POST /api/kyc/upload/            → upload a new document

Staff endpoints (prefix: /api/staff/kyc/)
  GET  /api/staff/kyc/pending/                          → review queue
  GET  /api/staff/kyc/users/{user_id}/documents/        → user's documents
  POST /api/staff/kyc/users/{user_id}/approve/          → approve entire KYC
  POST /api/staff/kyc/users/{user_id}/reject/           → reject entire KYC
  POST /api/staff/kyc/documents/{doc_id}/approve/       → approve one document
  POST /api/staff/kyc/documents/{doc_id}/reject/        → reject one document
"""
import logging

from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import HasPermission

from .exceptions import (
    KycAlreadyApprovedError,
    KycDocumentNotFoundError,
    KycIncompleteError,
    KycNotPendingError,
)
from .selectors import get_documents_for_user, get_pending_kyc_users
from .serializers import (
    KycDocumentSerializer,
    KycDocumentUploadSerializer,
    KycProfileSerializer,
    KycProfileSubmitSerializer,
    KycStatusSerializer,
    KycUserSummarySerializer,
    StaffApproveDocumentSerializer,
    StaffApproveKycSerializer,
    StaffRejectDocumentSerializer,
    StaffRejectKycSerializer,
)
from .services import (
    approve_kyc_document,
    approve_user_kyc,
    reject_kyc_document,
    reject_user_kyc,
    upload_kyc_document,
)
from .validators import validate_kyc_completeness

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Customer endpoints
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def kyc_status(request):
    """Return the authenticated user's KYC status and list of uploaded documents."""
    docs = get_documents_for_user(request.user.pk)
    profile = getattr(request.user, "kyc_profile", None)
    completeness = validate_kyc_completeness(user_id=request.user.pk)
    data = {
        "kyc_status": request.user.kyc_status,
        "profile": KycProfileSerializer(profile).data if profile else None,
        "documents": KycDocumentSerializer(docs, many=True, context={"request": request}).data,
        "completeness": {
            "is_valid": completeness.is_valid,
            "missing_fields": completeness.missing_fields,
            "missing_documents": completeness.missing_documents,
        },
    }
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def kyc_profile_get(request):
    profile = getattr(request.user, "kyc_profile", None)
    if not profile:
        return Response({"detail": "KYC profile not submitted."}, status=status.HTTP_404_NOT_FOUND)
    return Response(KycProfileSerializer(profile).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def kyc_profile_submit(request):
    """
    Create or update the user's KYC profile and advance user-level kyc_status
    to PENDING (unless already APPROVED).
    """
    ser = KycProfileSubmitSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    from django.utils import timezone
    from apps.users.models import User
    from apps.users.constants import KycStatus as UserKycStatus
    from .models import KycProfile

    profile, _ = KycProfile.objects.update_or_create(
        user=request.user,
        defaults={**ser.validated_data, "submitted_at": timezone.now()},
    )

    # Advance user kyc_status to PENDING unless already APPROVED
    if request.user.kyc_status != UserKycStatus.APPROVED:
        User.objects.filter(pk=request.user.pk).update(kyc_status=UserKycStatus.PENDING)
        request.user.kyc_status = UserKycStatus.PENDING

    return Response(KycProfileSerializer(profile).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def kyc_upload(request):
    """Upload a KYC document.  Advances user's kyc_status to PENDING."""
    ser = KycDocumentUploadSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    doc = upload_kyc_document(
        user=request.user,
        document_type=ser.validated_data["document_type"],
        file=ser.validated_data["file"],
    )
    return Response(KycDocumentSerializer(doc, context={"request": request}).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Staff endpoints
# ---------------------------------------------------------------------------

def _require_kyc_permission(request):
    if not HasPermission.user_has_perm(request.user, "review_kyc"):
        return Response(
            {"detail": "You do not have permission to review KYC."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_kyc_pending(request):
    """Return all users with kyc_status = PENDING (the review queue)."""
    err = _require_kyc_permission(request)
    if err:
        return err
    users = get_pending_kyc_users()
    ser = KycUserSummarySerializer(users, many=True)
    return Response(ser.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_user_documents(request, user_id: int):
    """Return all KYC documents for a given user."""
    err = _require_kyc_permission(request)
    if err:
        return err
    docs = get_documents_for_user(user_id)
    return Response(KycDocumentSerializer(docs, many=True, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def staff_approve_user_kyc(request, user_id: int):
    """Approve a user's entire KYC, granting financial access."""
    err = _require_kyc_permission(request)
    if err:
        return err

    ser = StaffApproveKycSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        logger.info(
            "Staff KYC approval attempt",
            extra={"staff_user_id": request.user.pk, "target_user_id": user_id},
        )
        user = approve_user_kyc(user_id=user_id, reviewed_by=request.user)
    except KycAlreadyApprovedError as exc:
        logger.info(
            "Staff KYC approval skipped: already approved",
            extra={"staff_user_id": request.user.pk, "target_user_id": user_id},
        )
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    except KycIncompleteError as exc:
        logger.info(
            "Staff KYC approval blocked: incomplete",
            extra={
                "staff_user_id": request.user.pk,
                "target_user_id": user_id,
                "missing_fields": exc.missing_fields,
                "missing_documents": exc.missing_documents,
            },
        )
        return Response(
            {
                "detail": "KYC incomplete.",
                "missing_fields": exc.missing_fields,
                "missing_documents": exc.missing_documents,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        logger.exception(
            "Staff KYC approval failed",
            extra={"staff_user_id": request.user.pk, "target_user_id": user_id},
        )
        return Response(
            {"detail": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    logger.info(
        "Staff KYC approval success",
        extra={"staff_user_id": request.user.pk, "target_user_id": user_id},
    )
    return Response({"detail": "KYC approved.", "kyc_status": user.kyc_status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def staff_reject_user_kyc(request, user_id: int):
    """Reject a user's KYC.  User may re-upload documents to restart the review."""
    err = _require_kyc_permission(request)
    if err:
        return err

    ser = StaffRejectKycSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = reject_user_kyc(
            user_id=user_id,
            reviewed_by=request.user,
            reason=ser.validated_data["reason"],
        )
    except KycNotPendingError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    except Exception:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    return Response({"detail": "KYC rejected.", "kyc_status": user.kyc_status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def staff_approve_document(request, doc_id: int):
    """Approve a single KYC document."""
    err = _require_kyc_permission(request)
    if err:
        return err

    ser = StaffApproveDocumentSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        doc = approve_kyc_document(
            doc_id=doc_id,
            reviewed_by=request.user,
            notes=ser.validated_data.get("notes", ""),
        )
    except KycDocumentNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

    return Response(KycDocumentSerializer(doc, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def staff_reject_document(request, doc_id: int):
    """Reject a single KYC document with a mandatory reason."""
    err = _require_kyc_permission(request)
    if err:
        return err

    ser = StaffRejectDocumentSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        doc = reject_kyc_document(
            doc_id=doc_id,
            reviewed_by=request.user,
            reason=ser.validated_data["reason"],
            notes=ser.validated_data.get("notes", ""),
        )
    except KycDocumentNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

    return Response(KycDocumentSerializer(doc, context={"request": request}).data)
