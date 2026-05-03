from __future__ import annotations

from dataclasses import dataclass

from apps.users.constants import KycStatus

from .constants import KycDocumentType, KycDocumentStatus
from .models import KycDocument, KycProfile


ID_DOCUMENT_TYPES: set[str] = {
    KycDocumentType.NATIONAL_ID,
    KycDocumentType.PASSPORT,
    KycDocumentType.RESIDENCE_PERMIT,
}


@dataclass(frozen=True)
class KycCompletenessResult:
    is_valid: bool
    missing_fields: list[str]
    missing_documents: list[str]


def validate_kyc_completeness(*, user_id: int) -> KycCompletenessResult:
    """
    Strict completeness validator:
      - Requires a submitted KycProfile with all required fields non-empty.
      - Requires at least one APPROVED identity document.

    Returns missing field keys and missing document requirements.
    """
    missing_fields: list[str] = []
    missing_documents: list[str] = []

    profile = KycProfile.objects.filter(user_id=user_id).first()
    if profile is None:
        missing_fields += [
            "legal_full_name",
            "date_of_birth",
            "nationality",
            "id_type",
            "id_number",
            "address_line1",
            "address_city",
            "address_country",
        ]
    else:
        required_field_names = [
            "legal_full_name",
            "date_of_birth",
            "nationality",
            "id_type",
            "id_number",
            "address_line1",
            "address_city",
            "address_country",
        ]
        for name in required_field_names:
            val = getattr(profile, name, None)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing_fields.append(name)

    has_approved_id = KycDocument.objects.filter(
        user_id=user_id,
        document_type__in=ID_DOCUMENT_TYPES,
        status=KycDocumentStatus.APPROVED,
    ).exists()
    if not has_approved_id:
        missing_documents.append("ID_DOCUMENT")

    is_valid = len(missing_fields) == 0 and len(missing_documents) == 0
    return KycCompletenessResult(
        is_valid=is_valid,
        missing_fields=missing_fields,
        missing_documents=missing_documents,
    )

# kyc/validators.py — implemented in later phases.
