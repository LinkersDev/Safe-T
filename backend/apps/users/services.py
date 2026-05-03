"""
Users app services — write operations only.
All business rules enforced here; views must not contain logic.
"""
from __future__ import annotations

from django.contrib.auth.hashers import make_password
from django.db import transaction as db_transaction
from django.utils import timezone

from .constants import RoleCode, UserStatus
from .exceptions import (
    InvalidApproverRoleError,
    PhoneAlreadyExistsError,
    UserAlreadyApprovedError,
    UserNotFoundError,
)
from .models import Permission, Role, RolePermission, User
from .validators import normalize_phone


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_user(
    *,
    phone: str,
    full_name: str,
    password: str,
    pin: str,
) -> User:
    """
    Creates a new customer account in PENDING_VERIFICATION state.

    Prerequisites:
      - Phone must already be verified via OTP (caller's responsibility).
      - The phone is normalised here for defence in depth; it should already
        be E.164 coming from the serializer.
    """
    normalized = normalize_phone(phone)

    if User.objects.filter(phone_number_normalized=normalized).exists():
        raise PhoneAlreadyExistsError(
            f"Phone number {phone} is already registered."
        )

    try:
        role = Role.objects.get(code=RoleCode.CUSTOMER)
    except Role.DoesNotExist:
        raise RuntimeError(
            "CUSTOMER role not found. Ensure seed migration has been applied."
        )

    user = User(
        phone_number=normalized,
        phone_number_normalized=normalized,
        full_name=full_name.strip(),
        role=role,
        status=UserStatus.PENDING_VERIFICATION,
        is_phone_verified=True,
        is_active=True,
    )
    user.set_password(password)          # argon2 via PASSWORD_HASHERS
    user.pin_hash = make_password(pin)   # argon2 for PIN
    user.save()
    return user


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def get_or_create_role(code: str) -> Role:
    return Role.objects.get(code=code)


# ---------------------------------------------------------------------------
# User approval lifecycle
# ---------------------------------------------------------------------------

def approve_user(*, user_id: int, staff_user: User) -> User:
    """
    Activate a PENDING_VERIFICATION user.
    Caller must pass a staff user with TELLER or ADMIN role.

    Atomically:
      1. Updates user status to ACTIVE.
      2. Creates a bank account for the user via accounts.services.create_account.
    If account creation fails the approval is rolled back.
    """
    _assert_can_approve(staff_user)

    with db_transaction.atomic():
        try:
            user = User.objects.select_for_update().get(pk=user_id)
        except User.DoesNotExist:
            raise UserNotFoundError(f"User {user_id} not found.")

        if user.status == UserStatus.ACTIVE:
            raise UserAlreadyApprovedError(f"User {user_id} is already active.")

        user.status = UserStatus.ACTIVE
        user.approved_by = staff_user
        user.approved_at = timezone.now()
        user.rejection_reason = ""
        user.save(update_fields=["status", "approved_by", "approved_at", "rejection_reason", "updated_at"])

        # Provision the customer's default account on first approval.
        # Import here to avoid circular imports at module load time.
        from apps.accounts.services import create_account
        create_account(user=user, created_by=staff_user)

    return user


def reject_user(*, user_id: int, staff_user: User, reason: str) -> User:
    """Reject a pending user with a mandatory reason."""
    _assert_can_approve(staff_user)

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise UserNotFoundError(f"User {user_id} not found.")

    if not reason.strip():
        raise ValueError("Rejection reason is required.")

    user.status = UserStatus.REJECTED
    user.rejection_reason = reason
    user.save(update_fields=["status", "rejection_reason", "updated_at"])
    return user


def block_user(*, user_id: int, staff_user: User, reason: str) -> User:
    """Block a user. Only Admin may do this."""
    if not _user_has_role(staff_user, RoleCode.ADMIN):
        raise InvalidApproverRoleError("Only Admin can block users.")

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise UserNotFoundError(f"User {user_id} not found.")

    user.status = UserStatus.BLOCKED
    user.blocked_reason = reason
    user.save(update_fields=["status", "blocked_reason", "updated_at"])
    return user


# ---------------------------------------------------------------------------
# Permission assignment
# ---------------------------------------------------------------------------

def assign_role_permission(
    *,
    role: Role,
    permission: Permission,
    granted_by: User | None = None,
) -> RolePermission:
    rp, _ = RolePermission.objects.get_or_create(
        role=role,
        permission=permission,
        defaults={"granted_by": granted_by},
    )
    return rp


# ---------------------------------------------------------------------------
# Internal guards
# ---------------------------------------------------------------------------

def _assert_can_approve(user: User) -> None:
    allowed = {RoleCode.TELLER, RoleCode.ADMIN}
    if not _user_has_any_role(user, allowed):
        raise InvalidApproverRoleError(
            "Only Teller or Admin can approve/reject users."
        )


def _user_has_role(user: User, role_code: str) -> bool:
    return bool(user.role and user.role.code == role_code)


def _user_has_any_role(user: User, role_codes: set[str]) -> bool:
    return bool(user.role and user.role.code in role_codes)
