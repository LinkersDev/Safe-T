"""
Teller-facing staff endpoints.

Design:
  - Always permission-gated by explicit permission codes (no role-based access).
  - Thin views: validate input → call services/selectors → return response.
"""

from __future__ import annotations

import secrets
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.selectors import get_account_by_id, get_account_by_number, get_accounts_for_user
from apps.accounts.serializers import AccountSerializer
from apps.accounts.exceptions import AccountRestrictedError, InsufficientFundsError
from apps.kyc.constants import KycDocumentType
from apps.ledger.constants import TransactionChannel, TransactionType
from apps.ledger.exceptions import KYCNotApprovedError, UserNotActiveError
from apps.ledger.services import post_transaction
from apps.users.constants import KycStatus, RoleCode, UserStatus
from apps.users.models import Role, User
from apps.users.permissions import HasPermission
from apps.users.selectors import get_user_by_phone
from apps.users.validators import normalize_phone


class RegisterCustomerSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=30)

    # Required KYC profile fields (bank-like)
    legal_full_name = serializers.CharField(max_length=255)
    date_of_birth = serializers.DateField()
    nationality = serializers.CharField(max_length=100)
    id_type = serializers.ChoiceField(
        choices=[
            KycDocumentType.NATIONAL_ID,
            KycDocumentType.PASSPORT,
            KycDocumentType.RESIDENCE_PERMIT,
        ]
    )
    id_number = serializers.CharField(max_length=100)
    address_line1 = serializers.CharField(max_length=255)
    address_city = serializers.CharField(max_length=120)
    address_country = serializers.CharField(max_length=120)

    # Required identity document upload
    document_type = serializers.ChoiceField(
        choices=[
            KycDocumentType.NATIONAL_ID,
            KycDocumentType.PASSPORT,
            KycDocumentType.RESIDENCE_PERMIT,
        ]
    )
    file = serializers.FileField()


def _random_password() -> str:
    # 12 chars, includes digits; avoids ambiguous chars.
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(12))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def register_customer_view(request: Request) -> Response:
    if not HasPermission.user_has_perm(request.user, "staff_register_customer"):
        return Response({"detail": "Permission denied.", "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    serializer = RegisterCustomerSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    full_name = data["full_name"].strip()

    try:
        phone = normalize_phone(data["phone_number"])
    except ValueError as exc:
        return Response({"detail": str(exc), "code": "invalid_phone"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(phone_number_normalized=phone).exists():
        return Response(
            {"detail": "This phone number is already registered.", "code": "phone_taken"},
            status=status.HTTP_409_CONFLICT,
        )

    role = Role.objects.get(code=RoleCode.CUSTOMER)
    # OTP-first onboarding: customer will set password + PIN on first login.
    temp_password = _random_password()

    from django.utils import timezone
    from apps.accounts.services import create_account
    from apps.kyc.models import KycProfile
    from apps.kyc.services import upload_kyc_document

    with transaction.atomic():
        user = User.objects.create_user(
            phone_number=phone,
            password=temp_password,
            full_name=full_name,
            role=role,
            status=UserStatus.ACTIVE,
            # Registration submits KYC, but financial access remains blocked until admin approval.
            kyc_status=KycStatus.PENDING,
            is_staff=False,
            is_superuser=False,
            is_active=True,
            is_phone_verified=True,
            first_login_completed=False,
        )

        KycProfile.objects.update_or_create(
            user=user,
            defaults={
                "legal_full_name": data["legal_full_name"].strip(),
                "date_of_birth": data["date_of_birth"],
                "nationality": data["nationality"].strip(),
                "id_type": data["id_type"],
                "id_number": data["id_number"].strip(),
                "address_line1": data["address_line1"].strip(),
                "address_city": data["address_city"].strip(),
                "address_country": data["address_country"].strip(),
                "submitted_at": timezone.now(),
            },
        )

        upload_kyc_document(
            user=user,
            document_type=data["document_type"],
            file=data["file"],
        )

        # Create default account
        account = create_account(user=user, created_by=request.user)

    return Response(
        {
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "phone_number": user.phone_number,
                "status": user.status,
                "kyc_status": user.kyc_status,
            },
            "account": AccountSerializer(account).data,
            "onboarding": {
                "first_login_completed": False,
                "next_step": "KYC submitted. Waiting for admin approval. Customer can login, but cannot transact until approved.",
            },
        },
        status=status.HTTP_201_CREATED,
    )


def _can_access_customer_profile(user) -> bool:
    # Admin/KYC reviewer flow only.
    return HasPermission.user_has_perm(user, "review_kyc")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_profile_view(request: Request, user_id: int) -> Response:
    """
    Teller-scoped customer profile view.
    This avoids giving Teller broad user-list access while enabling a
    post-registration "next steps" flow.
    """
    if not _can_access_customer_profile(request.user):
        return Response({"detail": "Permission denied.", "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    try:
        customer = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({"detail": "Customer not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    from apps.kyc.selectors import get_documents_for_user
    from apps.kyc.serializers import KycDocumentSerializer, KycProfileSerializer
    from apps.kyc.validators import validate_kyc_completeness

    docs = get_documents_for_user(customer.pk)
    profile = getattr(customer, "kyc_profile", None)
    completeness = validate_kyc_completeness(user_id=customer.pk)

    accounts = list(get_accounts_for_user(customer))
    return Response(
        {
            "user": {
                "id": customer.id,
                "full_name": customer.full_name,
                "phone_number": customer.phone_number,
                "status": customer.status,
                "kyc_status": customer.kyc_status,
            },
            "accounts": AccountSerializer(accounts, many=True).data,
            "kyc": {
                "profile": KycProfileSerializer(profile).data if profile else None,
                "documents": KycDocumentSerializer(docs, many=True, context={"request": request}).data,
                "completeness": {
                    "is_valid": completeness.is_valid,
                    "missing_fields": completeness.missing_fields,
                    "missing_documents": completeness.missing_documents,
                },
            },
        },
        status=status.HTTP_200_OK,
    )


class StaffKycProfileSubmitSerializer(serializers.Serializer):
    legal_full_name = serializers.CharField(max_length=255)
    date_of_birth = serializers.DateField()
    nationality = serializers.CharField(max_length=100)
    id_type = serializers.ChoiceField(choices=["NATIONAL_ID", "PASSPORT", "RESIDENCE_PERMIT"])
    id_number = serializers.CharField(max_length=100)
    address_line1 = serializers.CharField(max_length=255)
    address_city = serializers.CharField(max_length=120)
    address_country = serializers.CharField(max_length=120)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def customer_kyc_profile_submit_view(request: Request, user_id: int) -> Response:
    if not _can_access_customer_profile(request.user):
        return Response({"detail": "Permission denied.", "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    try:
        customer = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({"detail": "Customer not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    ser = StaffKycProfileSubmitSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    from django.utils import timezone
    from apps.kyc.models import KycProfile
    from apps.kyc.serializers import KycProfileSerializer

    profile, _ = KycProfile.objects.update_or_create(
        user=customer,
        defaults={**ser.validated_data, "submitted_at": timezone.now()},
    )

    # Advance user kyc_status to PENDING unless already APPROVED
    if customer.kyc_status != KycStatus.APPROVED:
        User.objects.filter(pk=customer.pk).update(kyc_status=KycStatus.PENDING)
        customer.kyc_status = KycStatus.PENDING

    return Response(KycProfileSerializer(profile).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def customer_kyc_document_upload_view(request: Request, user_id: int) -> Response:
    if not _can_access_customer_profile(request.user):
        return Response({"detail": "Permission denied.", "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    try:
        customer = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({"detail": "Customer not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    from apps.kyc.serializers import KycDocumentUploadSerializer, KycDocumentSerializer
    from apps.kyc.services import upload_kyc_document

    ser = KycDocumentUploadSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    doc = upload_kyc_document(
        user=customer,
        document_type=ser.validated_data["document_type"],
        file=ser.validated_data["file"],
    )
    return Response(KycDocumentSerializer(doc, context={"request": request}).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_lookup_view(request: Request) -> Response:
    """
    Staff lookup by phone number to open a customer profile without listing all users.
    Query params:
      - phone: +E.164 (preferred) or raw phone string
    """
    if not _can_access_customer_profile(request.user):
        return Response({"detail": "Permission denied.", "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    phone_raw = (request.query_params.get("phone") or "").strip()
    if not phone_raw:
        return Response({"detail": "Missing phone query param.", "code": "invalid_request"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        phone = normalize_phone(phone_raw)
    except ValueError as exc:
        return Response({"detail": str(exc), "code": "invalid_phone"}, status=status.HTTP_400_BAD_REQUEST)

    customer = get_user_by_phone(phone)
    if customer is None:
        return Response({"detail": "Customer not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    return Response({"user_id": customer.pk}, status=status.HTTP_200_OK)


class TellerTxSerializer(serializers.Serializer):
    lookup = serializers.CharField(max_length=60)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField(max_length=10, required=False, allow_blank=True)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True)


def _resolve_account(lookup: str, currency: str | None) -> tuple[object | None, Response | None]:
    value = (lookup or "").strip()
    if not value:
        return None, Response({"detail": "Missing lookup value.", "code": "invalid_request"}, status=status.HTTP_400_BAD_REQUEST)

    if value.startswith("+"):
        user = get_user_by_phone(value)
        if user is None:
            return None, Response({"detail": "Account not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)
        accounts = list(get_accounts_for_user(user))
        if not accounts:
            return None, Response({"detail": "Account not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)
        if currency:
            currency = currency.strip().upper()
            currency_candidates = [a for a in accounts if a.currency_id == currency]
            if currency_candidates:
                accounts = currency_candidates
        # Prefer the account with highest available balance
        return max(accounts, key=lambda a: a.available_balance), None

    # Otherwise assume account number (16 digits). We intentionally do not accept raw
    # numeric IDs here to avoid confusing lookups like "40" being treated as account_id=40.
    acc = get_account_by_number(value)
    return acc, None


def _get_cash_account(currency_code: str):
    cash_number = getattr(settings, "LEDGER_CASH_ACCOUNT_NUMBER", "")
    if not cash_number:
        return None
    return get_account_by_number(cash_number)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def deposit_view(request: Request) -> Response:
    if not HasPermission.user_has_perm(request.user, "staff_deposit"):
        return Response({"detail": "Permission denied.", "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    serializer = TellerTxSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    currency = (data.get("currency") or "USD").strip().upper()

    account, err = _resolve_account(data["lookup"], currency)
    if err is not None:
        return err
    if account is None:
        return Response({"detail": "Account not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    cash = _get_cash_account(currency)
    if cash is None:
        return Response({"detail": "Cash account is not configured.", "code": "cash_account_missing"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    description = (data.get("description") or "Staff deposit.").strip()
    try:
        tx = post_transaction(
            transaction_type=TransactionType.DEPOSIT,
            currency_code=currency,
            amount=Decimal(str(data["amount"])),
            source_account=cash,
            destination_account=account,
            description=description,
            channel=TransactionChannel.STAFF,
            initiated_by=request.user,
            customer=account.user,
            metadata={"teller_operation": "deposit"},
        )
    except KYCNotApprovedError as exc:
        return Response({"detail": str(exc), "code": "kyc_not_approved"}, status=status.HTTP_403_FORBIDDEN)
    except UserNotActiveError as exc:
        return Response({"detail": str(exc), "code": "user_not_active"}, status=status.HTTP_403_FORBIDDEN)
    except AccountRestrictedError as exc:
        return Response({"detail": str(exc), "code": "account_restricted"}, status=status.HTTP_403_FORBIDDEN)
    except InsufficientFundsError as exc:
        # Cash account / pool insufficient (should not happen in normal ops).
        return Response({"detail": str(exc), "code": "insufficient_funds"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    return Response({"transaction": {"reference_number": tx.reference_number, "status": tx.status}}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw_view(request: Request) -> Response:
    if not HasPermission.user_has_perm(request.user, "staff_withdraw"):
        return Response({"detail": "Permission denied.", "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    serializer = TellerTxSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    currency = (data.get("currency") or "USD").strip().upper()

    account, err = _resolve_account(data["lookup"], currency)
    if err is not None:
        return err
    if account is None:
        return Response({"detail": "Account not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    cash = _get_cash_account(currency)
    if cash is None:
        return Response({"detail": "Cash account is not configured.", "code": "cash_account_missing"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    description = (data.get("description") or "Staff withdrawal.").strip()
    try:
        tx = post_transaction(
            transaction_type=TransactionType.WITHDRAWAL,
            currency_code=currency,
            amount=Decimal(str(data["amount"])),
            source_account=account,
            destination_account=cash,
            description=description,
            channel=TransactionChannel.STAFF,
            initiated_by=request.user,
            customer=account.user,
            metadata={"teller_operation": "withdraw"},
        )
    except KYCNotApprovedError as exc:
        return Response({"detail": str(exc), "code": "kyc_not_approved"}, status=status.HTTP_403_FORBIDDEN)
    except UserNotActiveError as exc:
        return Response({"detail": str(exc), "code": "user_not_active"}, status=status.HTTP_403_FORBIDDEN)
    except AccountRestrictedError as exc:
        return Response({"detail": str(exc), "code": "account_restricted"}, status=status.HTTP_403_FORBIDDEN)
    except InsufficientFundsError as exc:
        return Response({"detail": str(exc), "code": "insufficient_funds"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    return Response({"transaction": {"reference_number": tx.reference_number, "status": tx.status}}, status=status.HTTP_201_CREATED)


class TellerTransactionListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    reference_number = serializers.CharField()
    transaction_type = serializers.CharField()
    status = serializers.CharField()
    currency_code = serializers.CharField(source="currency_id")
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    description = serializers.CharField()
    occurred_at = serializers.DateTimeField()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_transactions_view(request: Request, account_id: int) -> Response:
    if not HasPermission.user_has_perm(request.user, "staff_view_account_transactions"):
        return Response({"detail": "Permission denied.", "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    account = get_account_by_id(account_id)
    if account is None:
        return Response({"detail": "Account not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    from apps.ledger.models import Transaction

    limit = int(request.query_params.get("limit", "50") or 50)
    limit = max(1, min(limit, 500))

    txs = (
        Transaction.objects.filter(entries__account=account)
        .select_related("currency")
        .distinct()
        .order_by("-occurred_at")[:limit]
    )

    return Response(TellerTransactionListSerializer(txs, many=True).data, status=status.HTTP_200_OK)

