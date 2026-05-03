from __future__ import annotations

from dataclasses import dataclass

from apps.users.constants import KycStatus

from .validators import validate_kyc_completeness, KycCompletenessResult


def can_user_transact(user) -> bool:
    return bool(user and user.kyc_status == KycStatus.APPROVED)


@dataclass(frozen=True)
class ApprovalGuardResult:
    allowed: bool
    missing_fields: list[str]
    missing_documents: list[str]


def can_user_be_approved(user) -> ApprovalGuardResult:
    if not user:
        return ApprovalGuardResult(allowed=False, missing_fields=["user"], missing_documents=[])

    result: KycCompletenessResult = validate_kyc_completeness(user_id=user.pk)
    return ApprovalGuardResult(
        allowed=result.is_valid,
        missing_fields=result.missing_fields,
        missing_documents=result.missing_documents,
    )

