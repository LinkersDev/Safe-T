"""
Payments API views.

Customer-facing (/api/payments/):
  POST /api/payments/transfer/otp/       — request transfer OTP
  POST /api/payments/transfer/           — execute transfer
  POST /api/payments/p2p-receive-qr/issue/   — issue signed peer receive QR payload
  GET  /api/payments/p2p-receive-qr/resolve/ — resolve peer receive QR for payer preview
  POST /api/payments/qr/otp/             — request QR payment OTP
  POST /api/payments/qr/pay/             — execute QR payment
  GET  /api/payments/qr/{token}/         — resolve QR details
  GET  /api/payments/bill/providers/     — list active bill providers
  POST /api/payments/bill/fetch/         — fetch bill amount
  POST /api/payments/bill/otp/           — request bill payment OTP
  POST /api/payments/bill/pay/           — execute bill payment

Merchant-facing (/api/merchant/):
  GET  /api/merchant/profile/            — view own merchant profile
  POST /api/merchant/qr/generate/        — generate QR code
  GET  /api/merchant/qr/                 — list own QR codes
  GET  /api/merchant/transactions/       — merchant's transaction history
"""
import logging

from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.exceptions import AccountRestrictedError, InsufficientFundsError
from apps.accounts.models import Account
from apps.accounts.constants import AccountStatus
from apps.accounts.selectors import get_account_by_number, get_accounts_for_user
from apps.ledger.exceptions import DuplicateTransactionError, KYCNotApprovedError, UserNotActiveError
from apps.ledger.permissions import IsUserFullyActive
from apps.ledger.selectors import get_transactions_for_customer
from apps.ledger.serializers import TransactionSerializer
from apps.security.constants import OTPRequestType
from apps.security.exceptions import (
    OTPExpiredError,
    OTPInvalidError,
    OTPMaxAttemptsExceededError,
    OTPNotFoundError,
)
from apps.security.otp.policy import should_expose_dev_otp
from apps.security.throttling import OTPSendPhoneThrottle, OTPSendThrottle

from .exceptions import (
    BillProviderNotActiveError,
    BillProviderNotFoundError,
    MerchantNotActiveError,
    MerchantNotFoundError,
    QRTokenAlreadyPaidError,
    QRTokenExpiredError,
    QRTokenNotFoundError,
    TransferSameAccountError,
)
from .selectors import (
    get_active_bill_providers,
    get_merchant_by_user,
    get_qr_payment_by_token,
    get_qr_payments_for_merchant,
)
from .serializers import (
    BillFetchSerializer,
    BillPayExecuteSerializer,
    BillPayOTPSerializer,
    BillProviderSerializer,
    MerchantProfileSerializer,
    QRGenerateSerializer,
    QRPayExecuteSerializer,
    QRPaymentSerializer,
    QRPayOTPSerializer,
    TransferExecuteSerializer,
    TransferOTPSerializer,
)
from .p2p_receive_qr import P2PReceiveQrError, issue_receive_qr_string, resolve_receive_qr_string
from .services import (
    create_transfer,
    fetch_bill_info,
    generate_qr_code,
    process_bill_payment,
    process_qr_payment,
    send_bill_payment_otp,
    send_qr_payment_otp,
    send_transfer_otp,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")


def _device_id(request) -> str:
    return request.META.get("HTTP_X_DEVICE_ID", "")


def _otp_error(exc: Exception) -> Response:
    return Response(
        {"detail": str(exc)},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _resolve_source_account(user, account_number: str | None) -> Account | None:
    """Return the account by number (must belong to user) or first active account."""
    if account_number:
        acc = get_account_by_number(account_number)
        if acc is None or acc.user_id != user.pk:
            return None
        return acc
    accounts = list(get_accounts_for_user(user))
    return accounts[0] if accounts else None


def _resolve_destination_account(
    *,
    destination_account_number: str | None,
    destination_phone_number: str | None,
    currency_code: str,
) -> Account | None:
    if destination_account_number:
        return get_account_by_number(destination_account_number)

    if not destination_phone_number:
        return None

    from apps.users.selectors import get_user_by_phone

    user = get_user_by_phone(destination_phone_number)
    if user is None:
        return None

    accounts = list(get_accounts_for_user(user))
    active_accounts = [acc for acc in accounts if acc.status == AccountStatus.ACTIVE]
    if not active_accounts:
        return None

    currency_match = [acc for acc in active_accounts if acc.currency_id == currency_code]
    return (currency_match or active_accounts)[0]


# ---------------------------------------------------------------------------
# Transfer views
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transfer_recipient_lookup(request):
    """
    Resolve a destination phone number to a recipient display name.
    Authenticated-only to avoid user enumeration by anonymous callers.
    Query params:
      - phone: +E.164 or raw phone string
    """
    from apps.users.constants import RoleCode
    from apps.users.selectors import get_user_by_phone
    from apps.users.validators import normalize_phone

    phone_raw = (request.query_params.get("phone") or "").strip()
    if not phone_raw:
        return Response({"detail": "Missing phone query param.", "code": "invalid_request"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        phone = normalize_phone(phone_raw)
    except ValueError as exc:
        return Response({"detail": str(exc), "code": "invalid_phone"}, status=status.HTTP_400_BAD_REQUEST)

    user = get_user_by_phone(phone)
    if user is None or (user.role and user.role.code in RoleCode.STAFF_ROLES):
        return Response({"detail": "Customer not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    return Response({"user_id": user.pk, "full_name": user.full_name}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUserFullyActive])
@throttle_classes([OTPSendThrottle, OTPSendPhoneThrottle])
def transfer_otp(request):
    """Send a transfer OTP to the authenticated user's phone."""
    otp_plain = send_transfer_otp(
        user=request.user,
        ip=_client_ip(request),
        device_id=_device_id(request),
    )
    data = {"detail": "OTP sent. Enter it when submitting your transfer."}
    if should_expose_dev_otp(OTPRequestType.TRANSFER) and otp_plain:
        data["dev_otp"] = otp_plain
        data["_debug_otp"] = otp_plain
    return Response(data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUserFullyActive])
def transfer_execute(request):
    """Execute a transfer after OTP verification."""
    serializer = TransferExecuteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    pin = (data.get("pin") or "").strip()
    if not (pin and request.user.pin_hash and check_password(pin, request.user.pin_hash)):
        return Response({"detail": "Invalid PIN.", "code": "invalid_pin"}, status=status.HTTP_401_UNAUTHORIZED)

    source = _resolve_source_account(
        request.user, data.get("source_account_number")
    )
    if source is None:
        return Response(
            {"detail": "Source account not found or does not belong to you."},
            status=status.HTTP_404_NOT_FOUND,
        )

    dest = _resolve_destination_account(
        destination_account_number=data.get("destination_account_number") or None,
        destination_phone_number=data.get("destination_phone_number") or None,
        currency_code=data["currency_code"],
    )
    if dest is None:
        return Response(
            {"detail": "Destination account not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        tx = create_transfer(
            customer=request.user,
            source_account=source,
            destination_account=dest,
            amount=data["amount"],
            currency_code=data["currency_code"],
            description=data["description"],
            idempotency_key=data.get("idempotency_key") or None,
            ip=_client_ip(request),
            device_id=_device_id(request),
        )
    except TransferSameAccountError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except KYCNotApprovedError:
        logger.info(
            "Blocked transfer: KYC not approved",
            extra={"user_id": request.user.pk, "ip": _client_ip(request), "device_id": _device_id(request)},
        )
        return Response(
            {
                "detail": "KYC not approved. Complete verification to continue.",
                "code": "kyc_not_approved",
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    except (OTPExpiredError, OTPInvalidError, OTPMaxAttemptsExceededError, OTPNotFoundError) as exc:
        return _otp_error(exc)
    except InsufficientFundsError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except AccountRestrictedError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except DuplicateTransactionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    except UserNotActiveError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Peer receive QR (customer-to-customer)
# ---------------------------------------------------------------------------


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUserFullyActive])
def p2p_receive_qr_issue(request):
    """Issue a short-lived signed payload string embedded in the payer-facing QR."""
    try:
        qr_string, expires_in = issue_receive_qr_string(request.user)
    except P2PReceiveQrError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(
        {"qr_payload": qr_string, "expires_in_seconds": expires_in},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsUserFullyActive])
def p2p_receive_qr_resolve(request):
    """Resolve receive QR content into recipient identity for payer verification."""
    raw = (request.query_params.get("payload") or "").strip()
    try:
        data = resolve_receive_qr_string(raw)
    except P2PReceiveQrError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# QR Payment views
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUserFullyActive])
@throttle_classes([OTPSendThrottle, OTPSendPhoneThrottle])
def qr_pay_otp(request):
    """Send a QR payment OTP scoped to a specific QR token."""
    serializer = QRPayOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    otp_plain = send_qr_payment_otp(
        user=request.user,
        qr_token=serializer.validated_data["qr_token"],
        ip=_client_ip(request),
        device_id=_device_id(request),
    )
    data = {"detail": "OTP sent for QR payment."}
    if should_expose_dev_otp(OTPRequestType.QR_PAYMENT) and otp_plain:
        data["dev_otp"] = otp_plain
        data["_debug_otp"] = otp_plain
    return Response(data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def qr_resolve(request, qr_token):
    """Resolve QR token details (merchant name, amount, currency)."""
    qr = get_qr_payment_by_token(qr_token)
    if qr is None:
        return Response({"detail": "QR code not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(QRPaymentSerializer(qr).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUserFullyActive])
def qr_pay_execute(request):
    """Execute a QR payment after OTP verification."""
    serializer = QRPayExecuteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    payer_account = _resolve_source_account(request.user, data["source_account_number"])
    if payer_account is None:
        return Response(
            {"detail": "Payer account not found or does not belong to you."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        tx = process_qr_payment(
            payer=request.user,
            payer_account=payer_account,
            qr_token=data["qr_token"],
            otp_code=data["otp_code"],
            amount=data.get("amount"),
            idempotency_key=data.get("idempotency_key") or None,
        )
    except QRTokenNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except (QRTokenExpiredError, QRTokenAlreadyPaidError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    except KYCNotApprovedError:
        logger.info(
            "Blocked QR payment: KYC not approved",
            extra={"user_id": request.user.pk, "ip": _client_ip(request), "device_id": _device_id(request)},
        )
        return Response(
            {
                "detail": "KYC not approved. Complete verification to continue.",
                "code": "kyc_not_approved",
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    except (OTPExpiredError, OTPInvalidError, OTPMaxAttemptsExceededError, OTPNotFoundError) as exc:
        return _otp_error(exc)
    except InsufficientFundsError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except AccountRestrictedError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Bill Payment views
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bill_provider_list(request):
    """List active bill providers, optionally filtered by service_type."""
    service_type = request.query_params.get("service_type")
    providers = get_active_bill_providers(service_type=service_type)
    return Response(BillProviderSerializer(providers, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUserFullyActive])
def bill_fetch(request):
    """Fetch bill amount for a given provider and service number."""
    serializer = BillFetchSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        bill_info = fetch_bill_info(
            provider_code=data["provider_code"],
            service_number=data["service_number"],
        )
    except BillProviderNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except BillProviderNotActiveError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    return Response(bill_info)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUserFullyActive])
@throttle_classes([OTPSendThrottle, OTPSendPhoneThrottle])
def bill_pay_otp(request):
    """Send a bill payment OTP scoped to a specific provider + service number."""
    serializer = BillPayOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    otp_plain = send_bill_payment_otp(
        user=request.user,
        provider_code=data["provider_code"],
        service_number=data["service_number"],
        ip=_client_ip(request),
        device_id=_device_id(request),
    )
    resp = {"detail": "OTP sent for bill payment."}
    if should_expose_dev_otp(OTPRequestType.BILL_PAYMENT) and otp_plain:
        resp["dev_otp"] = otp_plain
        resp["_debug_otp"] = otp_plain
    return Response(resp, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUserFullyActive])
def bill_pay_execute(request):
    """Execute a bill payment after OTP verification."""
    serializer = BillPayExecuteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    payer_account = _resolve_source_account(request.user, data["source_account_number"])
    if payer_account is None:
        return Response(
            {"detail": "Source account not found or does not belong to you."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        tx = process_bill_payment(
            customer=request.user,
            payer_account=payer_account,
            provider_code=data["provider_code"],
            service_number=data["service_number"],
            bill_reference=data["bill_reference"],
            amount=data["amount"],
            otp_code=data["otp_code"],
            idempotency_key=data.get("idempotency_key") or None,
        )
    except BillProviderNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except KYCNotApprovedError:
        logger.info(
            "Blocked bill payment: KYC not approved",
            extra={"user_id": request.user.pk, "ip": _client_ip(request), "device_id": _device_id(request)},
        )
        return Response(
            {
                "detail": "KYC not approved. Complete verification to continue.",
                "code": "kyc_not_approved",
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    except (OTPExpiredError, OTPInvalidError, OTPMaxAttemptsExceededError, OTPNotFoundError) as exc:
        return _otp_error(exc)
    except InsufficientFundsError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except AccountRestrictedError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Merchant views (/api/merchant/)
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_profile(request):
    """Return the authenticated user's merchant profile."""
    profile = get_merchant_by_user(request.user)
    if profile is None:
        return Response({"detail": "No merchant profile found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(MerchantProfileSerializer(profile).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def merchant_qr_generate(request):
    """Generate a new QR code for the authenticated merchant."""
    serializer = QRGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        qr = generate_qr_code(
            merchant=request.user,
            currency_code=data["currency_code"],
            amount=data.get("amount"),
        )
    except MerchantNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except MerchantNotActiveError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    return Response(QRPaymentSerializer(qr).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_qr_list(request):
    """List all QR codes generated by the authenticated merchant."""
    profile = get_merchant_by_user(request.user)
    if profile is None:
        return Response({"detail": "No merchant profile found."}, status=status.HTTP_404_NOT_FOUND)

    qrs = get_qr_payments_for_merchant(profile)
    return Response(QRPaymentSerializer(qrs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_transactions(request):
    """List all transactions for the merchant's settlement account."""
    profile = get_merchant_by_user(request.user)
    if profile is None:
        return Response({"detail": "No merchant profile found."}, status=status.HTTP_404_NOT_FOUND)

    from apps.ledger.selectors import get_transactions_for_account
    from apps.ledger.serializers import TransactionListSerializer
    entries = get_transactions_for_account(
        profile.settlement_account,
        limit=int(request.query_params.get("limit", 50)),
        offset=int(request.query_params.get("offset", 0)),
    )
    from apps.ledger.serializers import TransactionEntrySerializer
    return Response(TransactionEntrySerializer(entries, many=True).data)
