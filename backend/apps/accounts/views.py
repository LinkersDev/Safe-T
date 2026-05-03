"""
Accounts app views.

Customer-facing:
  GET  /api/accounts/                    account_list
  GET  /api/accounts/{id}/               account_detail
  GET  /api/accounts/{id}/transactions/  account_transactions (stub — Phase 4)
  GET  /api/accounts/beneficiaries/      beneficiary_list
  POST /api/accounts/beneficiaries/      beneficiary_add
  DELETE /api/accounts/beneficiaries/{id}/ beneficiary_remove

Staff-facing (via staff_urls):
  GET  /api/staff/accounts/{id}/         staff_account_detail
  POST /api/staff/accounts/{id}/freeze/  freeze_account_view
  POST /api/staff/accounts/{id}/unfreeze/ unfreeze_account_view
  POST /api/staff/accounts/{id}/block/   block_account_view
  POST /api/staff/accounts/{id}/close/   close_account_view
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.users.constants import UserStatus
from apps.users.permissions import HasPermission, IsNotPending
from apps.users.selectors import get_user_by_phone

from .exceptions import (
    AccountAlreadyClosedError,
    AccountNotFoundError,
    BeneficiaryAlreadyExistsError,
    BeneficiaryNotFoundError,
)
from .permissions import IsAccountOwner
from .selectors import (
    get_account_by_id,
    get_account_by_number,
    get_accounts_for_user,
    get_active_beneficiaries,
)
from .constants import AccountStatus
from .serializers import (
    AccountRestrictionSerializer,
    AccountSerializer,
    StaffAccountSerializer,
    AddBeneficiarySerializer,
    BeneficiarySerializer,
    CloseAccountSerializer,
)
from .services import (
    add_beneficiary,
    block_account,
    close_account,
    deactivate_beneficiary,
    freeze_account,
    unblock_account,
    unfreeze_account,
)


# ---------------------------------------------------------------------------
# Customer — accounts
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsNotPending])
def account_list(request: Request) -> Response:
    """List all accounts owned by the authenticated user."""
    accounts = get_accounts_for_user(request.user)
    return Response(AccountSerializer(accounts, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsNotPending])
def account_detail(request: Request, account_id: int) -> Response:
    """Retrieve a single account. Must belong to the authenticated user."""
    account = get_account_by_id(account_id)
    if account is None:
        return Response(
            {"detail": "Account not found.", "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if account.user_id != request.user.pk:
        return Response(
            {"detail": "Access denied.", "code": "forbidden"},
            status=status.HTTP_403_FORBIDDEN,
        )
    return Response(AccountSerializer(account).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsNotPending])
def account_transactions(request: Request, account_id: int) -> Response:
    """
    Transaction history for an account.
    Stub — implemented in Phase 4 (ledger app).
    """
    account = get_account_by_id(account_id)
    if account is None or account.user_id != request.user.pk:
        return Response(
            {"detail": "Account not found.", "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {"detail": "Transaction history available in Phase 4.", "transactions": []},
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Customer — beneficiaries
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsNotPending])
def beneficiary_list_create(request: Request) -> Response:
    if request.method == "GET":
        beneficiaries = get_active_beneficiaries(request.user)
        return Response(BeneficiarySerializer(beneficiaries, many=True).data)

    # POST — add a beneficiary
    serializer = AddBeneficiarySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    account_number = serializer.validated_data["account_number"]
    destination = get_account_by_number(account_number)

    if destination is None:
        return Response(
            {"detail": "Destination account not found.", "code": "account_not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if destination.user_id == request.user.pk:
        return Response(
            {"detail": "You cannot add your own account as a beneficiary.", "code": "own_account"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        beneficiary = add_beneficiary(
            owner=request.user,
            destination_account=destination,
            nickname=serializer.validated_data["nickname"],
        )
    except BeneficiaryAlreadyExistsError:
        return Response(
            {"detail": "This account is already a beneficiary.", "code": "duplicate"},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(BeneficiarySerializer(beneficiary).data, status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def beneficiary_remove(request: Request, beneficiary_id: int) -> Response:
    try:
        deactivate_beneficiary(beneficiary_id=beneficiary_id, user=request.user)
    except BeneficiaryNotFoundError:
        return Response(
            {"detail": "Beneficiary not found.", "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Staff — account management
# ---------------------------------------------------------------------------

def _get_account_for_staff(account_id: int):
    """Helper shared by all staff account views."""
    return get_account_by_id(account_id)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_account_detail(request: Request, account_id: int) -> Response:
    if not HasPermission.user_has_perm(request.user, "view_all_accounts"):
        return Response(
            {"detail": "Permission denied.", "code": "forbidden"},
            status=status.HTTP_403_FORBIDDEN,
        )
    account = _get_account_for_staff(account_id)
    if account is None:
        return Response(
            {"detail": "Account not found.", "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(StaffAccountSerializer(account).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_account_lookup(request: Request) -> Response:
    """
    Staff helper: lookup an account by phone number or account number.
    Query params:
      - phone_number: E.164 phone (preferred)
      - account_number: 16-digit account number
    Returns: AccountSerializer for the resolved account.
    """
    if not HasPermission.user_has_perm(request.user, "view_all_accounts"):
        return Response(
            {"detail": "Permission denied.", "code": "forbidden"},
            status=status.HTTP_403_FORBIDDEN,
        )

    phone = (request.query_params.get("phone_number") or "").strip()
    account_number = (request.query_params.get("account_number") or "").strip()

    if not phone and not account_number:
        return Response(
            {"detail": "Provide 'phone_number' or 'account_number'.", "code": "invalid_request"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    account = None

    if account_number:
        account = get_account_by_number(account_number)

    if account is None and phone:
        user = get_user_by_phone(phone)
        if user is not None:
            currency = (request.query_params.get("currency") or "").strip().upper()
            accounts = list(get_accounts_for_user(user))
            active_accounts = [a for a in accounts if a.status == AccountStatus.ACTIVE]
            candidates = active_accounts or accounts

            if currency:
                currency_candidates = [a for a in candidates if a.currency_id == currency]
                candidates = currency_candidates or candidates

            # Prefer the account with the highest available balance
            account = max(candidates, key=lambda a: a.available_balance, default=None)

    if account is None:
        return Response(
            {"detail": "Account not found.", "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(StaffAccountSerializer(account).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def freeze_account_view(request: Request, account_id: int) -> Response:
    if not HasPermission.user_has_perm(request.user, "freeze_account"):
        return Response(
            {"detail": "Permission denied.", "code": "forbidden"},
            status=status.HTTP_403_FORBIDDEN,
        )
    account = _get_account_for_staff(account_id)
    if account is None:
        return Response(
            {"detail": "Account not found.", "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = AccountRestrictionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        freeze_account(
            account=account,
            reason=serializer.validated_data["reason"],
            applied_by=request.user,
        )
    except AccountAlreadyClosedError as e:
        return Response({"detail": str(e), "code": "already_closed"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "Account frozen successfully."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unfreeze_account_view(request: Request, account_id: int) -> Response:
    if not HasPermission.user_has_perm(request.user, "unfreeze_account"):
        return Response(
            {"detail": "Permission denied.", "code": "forbidden"},
            status=status.HTTP_403_FORBIDDEN,
        )
    account = _get_account_for_staff(account_id)
    if account is None:
        return Response(
            {"detail": "Account not found.", "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    unfreeze_account(account=account, released_by=request.user)
    return Response({"message": "Account unfrozen successfully."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def block_account_view(request: Request, account_id: int) -> Response:
    if not HasPermission.user_has_perm(request.user, "block_account"):
        return Response(
            {"detail": "Permission denied.", "code": "forbidden"},
            status=status.HTTP_403_FORBIDDEN,
        )
    account = _get_account_for_staff(account_id)
    if account is None:
        return Response(
            {"detail": "Account not found.", "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = AccountRestrictionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        block_account(
            account=account,
            reason=serializer.validated_data["reason"],
            applied_by=request.user,
        )
    except AccountAlreadyClosedError as e:
        return Response({"detail": str(e), "code": "already_closed"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "Account blocked successfully."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unblock_account_view(request: Request, account_id: int) -> Response:
    if not HasPermission.user_has_perm(request.user, "block_account"):
        return Response(
            {"detail": "Permission denied.", "code": "forbidden"},
            status=status.HTTP_403_FORBIDDEN,
        )
    account = _get_account_for_staff(account_id)
    if account is None:
        return Response(
            {"detail": "Account not found.", "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    unblock_account(account=account, released_by=request.user)
    return Response({"message": "Account unblocked successfully."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def close_account_view(request: Request, account_id: int) -> Response:
    if not HasPermission.user_has_perm(request.user, "block_account"):
        return Response(
            {"detail": "Permission denied.", "code": "forbidden"},
            status=status.HTTP_403_FORBIDDEN,
        )
    account = _get_account_for_staff(account_id)
    if account is None:
        return Response(
            {"detail": "Account not found.", "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = CloseAccountSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        close_account(
            account=account,
            reason=serializer.validated_data["reason"],
            closed_by=request.user,
        )
    except AccountAlreadyClosedError as e:
        return Response({"detail": str(e), "code": "already_closed"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "Account closed successfully."}, status=status.HTTP_200_OK)
