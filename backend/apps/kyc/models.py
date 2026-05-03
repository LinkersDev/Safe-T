"""KYC models."""
from django.conf import settings
from django.db import models

from .constants import KycDocumentStatus, KycDocumentType


class KycProfile(models.Model):
    """
    Structured KYC profile for a user (bank-like).

    This keeps identity fields out of the core User model and enables strict
    completeness validation before approval.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kyc_profile",
    )

    legal_full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=100)

    # ID metadata (matches the submitted document)
    id_type = models.CharField(
        max_length=50,
        choices=[
            (KycDocumentType.NATIONAL_ID, "National ID"),
            (KycDocumentType.PASSPORT, "Passport"),
            (KycDocumentType.RESIDENCE_PERMIT, "Residence Permit"),
        ],
    )
    id_number = models.CharField(max_length=100)

    address_line1 = models.CharField(max_length=255)
    address_city = models.CharField(max_length=120)
    address_country = models.CharField(max_length=120)

    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kyc_profiles"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["submitted_at"]),
        ]

    def __str__(self) -> str:
        return f"KycProfile(user={self.user_id})"


class KycDocument(models.Model):
    """
    A single identity document submitted by a user for KYC review.

    A user may have multiple documents (e.g. national ID + selfie).
    Staff reviews individual documents AND the overall kyc_status on
    the User model via the KYC service layer.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kyc_documents",
    )
    document_type = models.CharField(
        max_length=50,
        choices=KycDocumentType.CHOICES,
    )
    file = models.FileField(upload_to="kyc_documents/%Y/%m/")

    status = models.CharField(
        max_length=20,
        choices=KycDocumentStatus.CHOICES,
        default=KycDocumentStatus.PENDING,
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_kyc_documents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kyc_documents"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"], name="kyc_doc_user_status_idx"),
            models.Index(fields=["status"],          name="kyc_doc_status_idx"),
        ]

    def __str__(self) -> str:
        return f"KycDocument({self.document_type}, user={self.user_id}, status={self.status})"
