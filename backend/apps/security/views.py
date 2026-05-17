"""
Security app views — authentication endpoints.

All views are thin orchestrators:
  validate input → call service(s) → return response.
No business logic lives here.

Endpoint map
  POST /api/auth/register/               send_registration_otp
  POST /api/auth/register/complete/      complete_registration
  POST /api/auth/otp/send/               send_login_otp
  POST /api/auth/login/                  login_view
  POST /api/auth/reset-password/         send_password_reset_otp
  POST /api/auth/reset-password/confirm/ confirm_password_reset
  POST /api/auth/reset-pin/              send_pin_reset_otp
  POST /api/auth/reset-pin/confirm/      confirm_pin_reset
  POST /api/staff/users/<id>/unlock/     unlock_user_view   (staff_urls)
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.constants import RoleCode, UserStatus
from apps.users.exceptions import PhoneAlreadyExistsError
from apps.users.selectors import get_user_by_id, get_user_by_phone, get_user_permissions
from apps.users.services import register_user

from .constants import LoginStatus, OTPRequestType, ResetType
from .otp.factory import get_otp_service
from .otp.policy import should_expose_dev_otp
from .exceptions import (
    OTPExpiredError,
    OTPInvalidError,
    OTPMaxAttemptsExceededError,
    OTPNotFoundError,
)
from .serializers import (
    CompleteRegistrationSerializer,
    ConfirmPasswordResetSerializer,
    ConfirmPINResetSerializer,
    FirstLoginCompleteSerializer,
    FirstLoginSendOTPSerializer,
    LoginSerializer,
    SendLoginOTPSerializer,
    SendPasswordResetOTPSerializer,
    SendPINResetOTPSerializer,
    SendRegistrationOTPSerializer,
)
from .services import (
    check_and_auto_lock_user,
    record_login,
    record_password_reset,
    register_or_update_device,
    unlock_user,
)
from .throttling import LoginThrottle, OTPSendThrottle, OTPSendPhoneThrottle

logger = logging.getLogger("apps.security")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client_ip(request: Request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_device_id(request: Request) -> str:
    return request.META.get("HTTP_X_DEVICE_ID", "")


def _create_tokens(user) -> dict:
    """Mint JWT pair with custom claims for the client."""
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    access["role"] = user.role.code if user.role else None
    access["status"] = user.status
    access["full_name"] = user.full_name
    access["phone_number"] = user.phone_number
    access["kyc_status"] = getattr(user, "kyc_status", None)
    return {
        "access": str(access),
        "refresh": str(refresh),
    }


_OTP_ERROR_MAP = {
    OTPExpiredError: ("OTP has expired. Request a new one.", "otp_expired"),
    OTPInvalidError: ("Invalid OTP code.", "otp_invalid"),
    OTPMaxAttemptsExceededError: ("Maximum OTP attempts exceeded. Request a new OTP.", "otp_max_attempts"),
    OTPNotFoundError: ("No active OTP found. Request a new one.", "otp_not_found"),
}


def _otp_error_response(exc: Exception):
    msg, code = _OTP_ERROR_MAP.get(type(exc), ("OTP verification failed.", "otp_error"))
    return Response(
        {"detail": msg, "code": code},
        status=status.HTTP_400_BAD_REQUEST,
    )


# ---------------------------------------------------------------------------
# Registration — Step 1: send OTP
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([OTPSendThrottle])
def send_registration_otp(request: Request) -> Response:
    """
    Validates phone uniqueness and sends a REGISTRATION OTP.
    Returns HTTP 409 if the phone is already registered
    (acceptable in registration UX — user should know to log in instead).
    """
    serializer = SendRegistrationOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = serializer.validated_data["phone_number"]

    if get_user_by_phone(phone) is not None:
        return Response(
            {
                "detail": "This phone number is already registered.",
                "code": "phone_taken",
            },
            status=status.HTTP_409_CONFLICT,
        )

    otp_service = get_otp_service()
    issue = otp_service.generate_otp(
        phone=phone,
        request_type=OTPRequestType.REGISTRATION,
        ip_address=_get_client_ip(request),
        device_id=_get_device_id(request),
    )

    response_data: dict = {
        "message": "OTP sent to your phone.",
        "expires_in": 300,
    }

    # Expose OTP in response body only during development
    if issue.otp_plain:
        response_data["dev_otp"] = issue.otp_plain
        response_data["_debug_otp"] = issue.otp_plain

    return Response(response_data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Registration — Step 2: verify OTP + create user
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
def complete_registration(request: Request) -> Response:
    """
    Verifies REGISTRATION OTP and creates a PENDING_VERIFICATION user.
    """
    serializer = CompleteRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    phone = data["phone_number"]

    otp_service = get_otp_service()
    try:
        otp_service.verify_otp(
            phone=phone,
            request_type=OTPRequestType.REGISTRATION,
            otp_code=data["otp_code"],
        )
    except (OTPExpiredError, OTPInvalidError, OTPMaxAttemptsExceededError, OTPNotFoundError) as exc:
        return _otp_error_response(exc)

    try:
        user = register_user(
            phone=phone,
            full_name=data["full_name"],
            password=data["password"],
            pin=data["pin"],
        )
    except PhoneAlreadyExistsError:
        return Response(
            {"detail": "This phone number is already registered.", "code": "phone_taken"},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {
            "message": "Account created. Awaiting staff verification before first login.",
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "phone_number": user.phone_number,
                "status": user.status,
            },
        },
        status=status.HTTP_201_CREATED,
    )


# ---------------------------------------------------------------------------
# Login — Step 1: send OTP
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([OTPSendThrottle, OTPSendPhoneThrottle])
def send_login_otp(request: Request) -> Response:
    """
    Sends a LOGIN OTP.
    Returns the same response whether the phone exists or not
    to prevent user-enumeration attacks.
    """
    serializer = SendLoginOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = serializer.validated_data["phone_number"]
    user = get_user_by_phone(phone)

    # Policy: issue LOGIN OTP for existing active customers (enumeration-safe response).
    otp_plain: str | None = None
    if (
        user is not None
        and user.status != UserStatus.BLOCKED
        and getattr(user, "first_login_completed", True) is True
        and (user.role is None or user.role.code not in RoleCode.STAFF_ROLES)
    ):
        otp_service = get_otp_service()
        issue = otp_service.generate_otp(
            phone=phone,
            request_type=OTPRequestType.LOGIN,
            ip_address=_get_client_ip(request),
            device_id=_get_device_id(request),
            user=user,
        )
        otp_plain = issue.get("otp")

    response_data: dict = {
        "message": "If this number is registered, an OTP has been sent.",
    }

    if otp_plain and should_expose_dev_otp(OTPRequestType.LOGIN):
        response_data["dev_otp"] = otp_plain
        response_data["_debug_otp"] = otp_plain

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([OTPSendThrottle])
def send_first_login_otp(request: Request) -> Response:
    serializer = FirstLoginSendOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = serializer.validated_data["phone_number"]
    user = get_user_by_phone(phone)

    otp_plain: str | None = None
    if (
        user is not None
        and user.status != UserStatus.BLOCKED
        and getattr(user, "first_login_completed", True) is False
    ):
        otp_service = get_otp_service()
        issue = otp_service.generate_otp(
            phone=phone,
            request_type=OTPRequestType.FIRST_LOGIN,
            ip_address=_get_client_ip(request),
            device_id=_get_device_id(request),
            user=user,
        )
        otp_plain = issue.get("otp")

    data: dict = {"message": "If this number is registered, an OTP has been sent.", "expires_in": 300}
    if otp_plain:
        data["dev_otp"] = otp_plain
        data["_debug_otp"] = otp_plain
    return Response(data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def complete_first_login(request: Request) -> Response:
    """
    OTP-first onboarding: verify OTP then force-set password + PIN.
    """
    serializer = FirstLoginCompleteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    phone = data["phone_number"]
    ip = _get_client_ip(request)
    device_id = _get_device_id(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    user = get_user_by_phone(phone)
    if user is None:
        return Response({"detail": "Invalid request.", "code": "invalid_request"}, status=status.HTTP_400_BAD_REQUEST)

    if getattr(user, "first_login_completed", True) is True:
        return Response({"detail": "First login already completed.", "code": "already_completed"}, status=status.HTTP_409_CONFLICT)

    otp_service = get_otp_service()
    try:
        otp_service.verify_otp(
            phone=phone,
            request_type=OTPRequestType.FIRST_LOGIN,
            otp_code=data["otp_code"],
        )
    except (OTPExpiredError, OTPInvalidError, OTPMaxAttemptsExceededError, OTPNotFoundError) as exc:
        return _otp_error_response(exc)

    user.set_password(data["password"])
    user.pin_hash = make_password(data["pin"])
    user.first_login_completed = True
    user.save(update_fields=["password", "pin_hash", "first_login_completed", "updated_at"])

    register_or_update_device(
        user=user,
        device_uuid=device_id or f"web_{user.pk}",
        device_hash=device_id,
        ip=ip,
    )
    record_login(
        phone=phone,
        user=user,
        status=LoginStatus.SUCCESS,
        ip=ip,
        device_id=device_id,
        user_agent=user_agent,
    )

    permissions = list(get_user_permissions(user).values_list("code", flat=True))
    tokens = _create_tokens(user)
    return Response(
        {
            **tokens,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "phone_number": user.phone_number,
                "status": user.status,
                "role": user.role.code if user.role else None,
            },
            "permissions": permissions,
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Login — Step 2: verify OTP + credentials → JWT
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def login_view(request: Request) -> Response:
    """
    Authenticates with phone + OTP + password (or PIN).
    Records every attempt. Auto-locks after N consecutive failures.
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    phone = data["phone_number"]
    ip = _get_client_ip(request)
    device_id = _get_device_id(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    user = get_user_by_phone(phone)

    if user is None:
        record_login(
            phone=phone,
            status=LoginStatus.FAILED,
            failure_reason="user_not_found",
            ip=ip,
        )
        return Response(
            {"detail": "Phone number is not registered.", "code": "phone_not_registered"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Reject BLOCKED accounts before doing any further work
    if user.status == UserStatus.BLOCKED:
        record_login(
            phone=phone,
            user=user,
            status=LoginStatus.FAILED,
            failure_reason="account_blocked",
            ip=ip,
        )
        return Response(
            {
                "detail": "Your account has been blocked. Contact support.",
                "code": "account_blocked",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # Reject locked accounts (failed-attempt lock)
    if not user.is_active:
        record_login(
            phone=phone,
            user=user,
            status=LoginStatus.FAILED,
            failure_reason="account_locked",
            ip=ip,
        )
        return Response(
            {
                "detail": (
                    "Your account is temporarily locked due to multiple failed attempts. "
                    "Contact customer service to unlock."
                ),
                "code": "account_locked",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # Enforce OTP-first onboarding for staff-registered customers
    if getattr(user, "first_login_completed", True) is False:
        return Response(
            {
                "detail": "First login setup required. Request an OTP to set password and PIN.",
                "code": "first_login_required",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # Verify password or PIN
    password = data.get("password", "")
    pin = data.get("pin", "")
    otp_code = (data.get("otp_code") or "").strip()

    credential_valid = False
    if password:
        credential_valid = user.check_password(password)
    if not credential_valid and pin:
        credential_valid = bool(user.pin_hash) and check_password(pin, user.pin_hash)

    if not credential_valid:
        wrong_code = "wrong_credentials"
        wrong_detail = "Invalid credentials."
        if password:
            wrong_code = "wrong_password"
            wrong_detail = "Wrong password."
        elif pin:
            wrong_code = "wrong_pin"
            wrong_detail = "Wrong PIN."

        record_login(
            phone=phone,
            user=user,
            status=LoginStatus.FAILED,
            failure_reason="wrong_credential",
            ip=ip,
            device_id=device_id,
            user_agent=user_agent,
        )
        check_and_auto_lock_user(user=user, phone=phone)
        return Response(
            {"detail": wrong_detail, "code": wrong_code},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Customers must also pass a LOGIN OTP on every login.
    is_customer = user.role is not None and user.role.code not in RoleCode.STAFF_ROLES
    if is_customer:
        if not otp_code:
            return Response(
                {"detail": "OTP code is required.", "code": "otp_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        otp_service = get_otp_service()
        try:
            otp_service.verify_otp(
                phone=phone,
                request_type=OTPRequestType.LOGIN,
                otp_code=otp_code,
            )
        except (OTPExpiredError, OTPInvalidError, OTPMaxAttemptsExceededError, OTPNotFoundError) as exc:
            return _otp_error_response(exc)

    # Success
    register_or_update_device(
        user=user,
        device_uuid=device_id or f"web_{user.pk}",
        device_hash=device_id,
        ip=ip,
    )
    record_login(
        phone=phone,
        user=user,
        status=LoginStatus.SUCCESS,
        ip=ip,
        device_id=device_id,
        user_agent=user_agent,
    )
    user.__class__.objects.filter(pk=user.pk).update(last_login_at=timezone.now())

    permissions = list(
        get_user_permissions(user).values_list("code", flat=True)
    )

    tokens = _create_tokens(user)
    return Response(
        {
            **tokens,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "phone_number": user.phone_number,
                "status": user.status,
                "role": user.role.code if user.role else None,
            },
            "permissions": permissions,
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([OTPSendThrottle])
def send_password_reset_otp(request: Request) -> Response:
    """
    Sends a PASSWORD_RESET OTP.
    Always returns the same generic response (enumeration protection).
    """
    serializer = SendPasswordResetOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = serializer.validated_data["phone_number"]
    user = get_user_by_phone(phone)

    otp_plain: str | None = None
    if user is not None and user.status == UserStatus.ACTIVE:
        otp_service = get_otp_service()
        issue = otp_service.generate_otp(
            phone=phone,
            request_type=OTPRequestType.PASSWORD_RESET,
            ip_address=_get_client_ip(request),
            user=user,
        )
        otp_plain = issue.get("otp")

    response_data: dict = {
        "message": "If this number is registered and active, an OTP has been sent.",
    }
    if otp_plain:
        response_data["dev_otp"] = otp_plain
        response_data["_debug_otp"] = otp_plain

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def confirm_password_reset(request: Request) -> Response:
    """Verifies PASSWORD_RESET OTP and sets a new password."""
    serializer = ConfirmPasswordResetSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    phone = data["phone_number"]
    ip = _get_client_ip(request)

    user = get_user_by_phone(phone)
    if user is None or user.status != UserStatus.ACTIVE:
        return Response(
            {"detail": "Invalid request.", "code": "invalid_request"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        otp_service = get_otp_service()
        otp_request = otp_service.verify_otp(
            phone=phone,
            request_type=OTPRequestType.PASSWORD_RESET,
            otp_code=data["otp_code"],
        )
    except (OTPExpiredError, OTPInvalidError, OTPMaxAttemptsExceededError, OTPNotFoundError) as exc:
        return _otp_error_response(exc)

    user.set_password(data["new_password"])
    user.save(update_fields=["password", "updated_at"])

    record_password_reset(
        user=user,
        reset_type=ResetType.PASSWORD,
        otp_request=otp_request,
        ip_address=ip,
        success=True,
    )
    return Response(
        {"message": "Password updated successfully."},
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# PIN reset
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([OTPSendThrottle, OTPSendPhoneThrottle])
def send_pin_reset_otp(request: Request) -> Response:
    """
    Sends a PIN_RESET OTP.
    Always returns the same generic response (enumeration protection).
    """
    serializer = SendPINResetOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = serializer.validated_data["phone_number"]
    user = get_user_by_phone(phone)

    otp_plain: str | None = None
    if user is not None and user.status == UserStatus.ACTIVE:
        otp_service = get_otp_service()
        issue = otp_service.generate_otp(
            phone=phone,
            request_type=OTPRequestType.PIN_RESET,
            ip_address=_get_client_ip(request),
            user=user,
        )
        otp_plain = issue.get("otp")

    response_data: dict = {
        "message": "If this number is registered and active, an OTP has been sent.",
    }
    if otp_plain:
        response_data["dev_otp"] = otp_plain
        response_data["_debug_otp"] = otp_plain

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def confirm_pin_reset(request: Request) -> Response:
    """Verifies PIN_RESET OTP and sets a new PIN."""
    serializer = ConfirmPINResetSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    phone = data["phone_number"]
    ip = _get_client_ip(request)

    user = get_user_by_phone(phone)
    if user is None or user.status != UserStatus.ACTIVE:
        return Response(
            {"detail": "Invalid request.", "code": "invalid_request"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        otp_service = get_otp_service()
        otp_request = otp_service.verify_otp(
            phone=phone,
            request_type=OTPRequestType.PIN_RESET,
            otp_code=data["otp_code"],
        )
    except (OTPExpiredError, OTPInvalidError, OTPMaxAttemptsExceededError, OTPNotFoundError) as exc:
        return _otp_error_response(exc)

    user.pin_hash = make_password(data["new_pin"])
    user.save(update_fields=["pin_hash", "updated_at"])

    record_password_reset(
        user=user,
        reset_type=ResetType.PIN,
        otp_request=otp_request,
        ip_address=ip,
        success=True,
    )
    return Response(
        {"message": "PIN updated successfully."},
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Staff: Unlock user (Customer Service or Admin only)
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unlock_user_view(request: Request, user_id: int) -> Response:
    """
    Unlocks a user's login access.
    Requires 'unlock_user' permission (Customer Service, Admin).
    """
    from apps.users.permissions import HasPermission

    if not HasPermission.user_has_perm(request.user, "unlock_user"):
        return Response(
            {"detail": "You do not have permission to unlock users.", "code": "forbidden"},
            status=status.HTTP_403_FORBIDDEN,
        )

    target = get_user_by_id(user_id)
    if target is None:
        return Response(
            {"detail": "User not found.", "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if target.status == UserStatus.BLOCKED:
        return Response(
            {
                "detail": "User is blocked. Only Admin can unblock via the user management endpoint.",
                "code": "user_blocked",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    unlock_user(user=target, unlocked_by=request.user)

    return Response(
        {"message": f"User {target.phone_number} has been unlocked."},
        status=status.HTTP_200_OK,
    )
