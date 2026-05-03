"""
Users app selectors — read-only queries.
"""
from __future__ import annotations

from django.db.models import QuerySet

from .constants import UserStatus
from .models import Permission, Role, User


def get_user_by_phone(phone: str) -> User | None:
    try:
        return User.objects.select_related("role").get(phone_number_normalized=phone)
    except User.DoesNotExist:
        return None


def get_user_by_id(user_id: int) -> User | None:
    try:
        return User.objects.select_related("role").get(pk=user_id)
    except User.DoesNotExist:
        return None


def get_pending_users() -> QuerySet[User]:
    return (
        User.objects.select_related("role")
        .filter(status=UserStatus.PENDING_VERIFICATION)
        .order_by("created_at")
    )


def get_all_users(*, search: str = "", limit: int = 500) -> QuerySet[User]:
    """
    Staff-facing user list.
    Lightweight (no pagination yet): capped to a sane default limit.
    """
    qs = User.objects.select_related("role").order_by("-created_at")
    if search:
        qs = qs.filter(phone_number__icontains=search) | qs.filter(full_name__icontains=search)
    return qs[: max(1, min(limit, 2000))]


def get_user_permissions(user: User) -> QuerySet[Permission]:
    if not user.role:
        return Permission.objects.none()
    return Permission.objects.filter(
        permission_roles__role=user.role
    ).distinct()


def get_role_by_code(code: str) -> Role | None:
    try:
        return Role.objects.get(code=code)
    except Role.DoesNotExist:
        return None
