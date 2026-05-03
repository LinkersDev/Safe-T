"""
Users app views — Phase 1 stubs.
Full implementation in Phase 2 (auth) and Phase 6 (KYC/activation).
"""
import secrets

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from .permissions import IsAdminRole, HasPermission
from .selectors import get_all_users, get_pending_users
from .serializers import StaffRegisterSerializer, UserSerializer
from .services import approve_user, reject_user
from .models import Role, StaffProfile, User
from .constants import RoleCode, UserStatus
from .validators import normalize_phone


@api_view(["GET"])
@permission_classes([IsAdminRole])
def pending_users_list(request: Request) -> Response:
    users = get_pending_users()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAdminRole])
def users_list(request: Request) -> Response:
    search = request.query_params.get("search", "") or ""
    limit = int(request.query_params.get("limit", "500") or 500)
    users = get_all_users(search=search, limit=limit)
    return Response(UserSerializer(users, many=True).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAdminRole])
def approve_user_view(request: Request, pk: int) -> Response:
    user = approve_user(user_id=pk, staff_user=request.user)
    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([IsAdminRole])
def reject_user_view(request: Request, pk: int) -> Response:
    reason = request.data.get("reason", "")
    user = reject_user(user_id=pk, staff_user=request.user, reason=reason)
    return Response(UserSerializer(user).data)


def _random_password() -> str:
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(12))


@api_view(["POST"])
@permission_classes([IsAdminRole])
def register_staff_user(request: Request) -> Response:
    """
    Admin creates a staff user with OTP-first onboarding.
    Staff sets their own password + PIN after first-login OTP verification.
    """
    if not HasPermission.user_has_perm(request.user, "view_all_users"):
        return Response({"detail": "Permission denied.", "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    ser = StaffRegisterSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    data = ser.validated_data
    try:
        phone = normalize_phone(data["phone_number"])
    except ValueError as exc:
        return Response({"detail": str(exc), "code": "invalid_phone"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(phone_number_normalized=phone).exists():
        return Response({"detail": "This phone number is already registered.", "code": "phone_taken"}, status=status.HTTP_409_CONFLICT)

    role = Role.objects.filter(code=data["role_code"]).first()
    if role is None or not role.is_staff_role:
        return Response({"detail": "Invalid staff role.", "code": "invalid_role"}, status=status.HTTP_400_BAD_REQUEST)

    temp_password = _random_password()

    with transaction.atomic():
        user = User.objects.create_user(
            phone_number=phone,
            password=temp_password,
            full_name=data["full_name"].strip(),
            role=role,
            status=UserStatus.ACTIVE,
            is_staff=True,
            is_superuser=(role.code == RoleCode.ADMIN),
            is_active=True,
            is_phone_verified=True,
            first_login_completed=False,
        )

        StaffProfile.objects.update_or_create(
            user=user,
            defaults={
                "employee_id": data.get("employee_id", "") or "",
                "department": data.get("department", "") or "",
                "branch": data.get("branch", "") or "",
                "job_title": data.get("job_title", "") or "",
                "address_line1": data.get("address_line1", "") or "",
                "address_city": data.get("address_city", "") or "",
                "address_country": data.get("address_country", "") or "",
            },
        )

    return Response(
        {
            "user": UserSerializer(user).data,
            "onboarding": {"first_login_completed": False, "next_step": "Staff must complete OTP-first login to set password and PIN."},
        },
        status=status.HTTP_201_CREATED,
    )
