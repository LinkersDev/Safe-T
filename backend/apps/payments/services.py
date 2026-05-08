"""
Payments write-path services.

All three payment types (Transfer, QR, Bill) follow the same pattern:
  1. Verify OTP for the correct payment type
  2. Validate accounts and constraints
  3. Call post_transaction() — the single atomic ledger function
  4. Write the payment-type satellite record
"""
import hashlib
import logging
import secrets
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import Account
from apps.accounts.selectors import assert_account_can_debit
from apps.ledger.constants import TransactionChannel, TransactionType
from apps.ledger.services import post_transaction
from apps.security.constants import OTPRequestType
from apps.security.services import create_otp
from apps.users.constants import UserStatus

from .constants import QR_TOKEN_TTL_HOURS, QRAmountMode, QRPaymentStatus
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
from .models import BillPayment, BillProvider, MerchantProfile, QRPayment

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------

def send_transfer_otp(
    *,
    user,
    ip: str = "",
    device_id: str = "",
) -> str:
    """Issue an OTP for a pending transfer. Returns plaintext OTP (never persisted)."""
    _, otp_plain = create_otp(
        phone=user.phone_number,
        request_type=OTPRequestType.TRANSFER,
        purpose_ref="TRANSFER",
        ip=ip,
        device_id=device_id,
        user=user,
    )
    return otp_plain


def create_transfer(
    *,
    customer,
    source_account: Account,
    destination_account: Account,
    amount: Decimal,
    currency_code: str,
    description: str = "",
    idempotency_key: str | None = None,
    channel: str = TransactionChannel.MOBILE,
    ip: str = "",
    device_id: str = "",
) -> "Transaction":  # noqa: F821
    """
    Execute a customer-to-customer transfer.

    Flow:
      1. Reject same-account transfers early.
      2. Call post_transaction() which handles locking, balance checks,
         double-entry, and fee collection atomically.
    """
    if source_account.pk == destination_account.pk:
        raise TransferSameAccountError("Source and destination accounts must differ.")

    transaction = post_transaction(
        transaction_type=TransactionType.TRANSFER,
        currency_code=currency_code,
        amount=Decimal(str(amount)),
        source_account=source_account,
        destination_account=destination_account,
        description=description or "Transfer",
        channel=channel,
        initiated_by=customer,
        customer=customer,
        idempotency_key=idempotency_key,
        requires_otp=False,
    )

    logger.info(
        "Transfer completed | ref=%s amount=%s src=%s dst=%s",
        transaction.reference_number,
        amount,
        source_account.account_number,
        destination_account.account_number,
    )
    return transaction


# ---------------------------------------------------------------------------
# QR Payment
# ---------------------------------------------------------------------------

def generate_qr_code(
    *,
    merchant: "User",  # noqa: F821
    currency_code: str = "USD",
    amount: Decimal | None = None,
) -> QRPayment:
    """
    Generate a QR code for a merchant.

    If amount is provided → FIXED mode (payer sees fixed amount).
    If amount is None    → OPEN  mode (payer enters the amount).
    """
    try:
        profile = MerchantProfile.objects.select_related("settlement_account").get(
            user=merchant
        )
    except MerchantProfile.DoesNotExist:
        raise MerchantNotFoundError("No merchant profile found for this user.")

    from .constants import MerchantStatus
    if profile.status != MerchantStatus.ACTIVE:
        raise MerchantNotActiveError(
            f"Merchant profile is not active (status={profile.status})."
        )

    token = secrets.token_urlsafe(32)
    payload = f"{profile.pk}:{currency_code}:{amount}:{token}"
    payload_hash = hashlib.sha256(payload.encode()).hexdigest()

    return QRPayment.objects.create(
        merchant_profile=profile,
        merchant_account=profile.settlement_account,
        qr_token=token,
        qr_payload_hash=payload_hash,
        amount_mode=QRAmountMode.FIXED if amount is not None else QRAmountMode.OPEN,
        display_amount=amount,
        currency_id=currency_code,
        expires_at=timezone.now() + timezone.timedelta(hours=QR_TOKEN_TTL_HOURS),
    )


def send_qr_payment_otp(
    *,
    user,
    qr_token: str,
    ip: str = "",
    device_id: str = "",
) -> str:
    """Issue an OTP scoped to a specific QR payment (token used as purpose_ref). Returns plaintext OTP."""
    _, otp_plain = create_otp(
        phone=user.phone_number,
        request_type=OTPRequestType.QR_PAYMENT,
        purpose_ref=qr_token,
        ip=ip,
        device_id=device_id,
        user=user,
    )
    return otp_plain


def process_qr_payment(
    *,
    payer,
    payer_account: Account,
    qr_token: str,
    otp_code: str,
    amount: Decimal | None = None,
    idempotency_key: str | None = None,
    channel: str = TransactionChannel.MOBILE,
) -> "Transaction":  # noqa: F821
    """
    Execute a QR payment.

    For FIXED QR codes the amount is taken from display_amount.
    For OPEN QR codes the caller must provide the amount.
    """
    try:
        qr = QRPayment.objects.select_related(
            "merchant_profile", "merchant_account", "currency"
        ).get(qr_token=qr_token)
    except QRPayment.DoesNotExist:
        raise QRTokenNotFoundError(f"QR token not found.")

    if qr.status == QRPaymentStatus.PAID:
        raise QRTokenAlreadyPaidError("This QR code has already been paid.")

    if qr.status != QRPaymentStatus.PENDING or qr.expires_at < timezone.now():
        # Mark expired if still PENDING and TTL has elapsed
        if qr.status == QRPaymentStatus.PENDING:
            QRPayment.objects.filter(pk=qr.pk).update(status=QRPaymentStatus.EXPIRED)
        raise QRTokenExpiredError("This QR code has expired.")

    pay_amount = (
        qr.display_amount
        if qr.amount_mode == QRAmountMode.FIXED
        else Decimal(str(amount))
    )
    if pay_amount is None or pay_amount <= 0:
        raise ValueError("A positive payment amount is required.")

    # Verify OTP scoped to this specific QR token
    otp_req = verify_otp(
        phone=payer.phone_number,
        request_type=OTPRequestType.QR_PAYMENT,
        otp_plain=otp_code,
        purpose_ref=qr_token,
    )

    # Record scan time
    QRPayment.objects.filter(pk=qr.pk).update(scanned_at=timezone.now())

    transaction = post_transaction(
        transaction_type=TransactionType.QR_PAYMENT,
        currency_code=qr.currency_id,
        amount=pay_amount,
        source_account=payer_account,
        destination_account=qr.merchant_account,
        description=f"QR payment to {qr.merchant_profile.business_name}",
        channel=channel,
        initiated_by=payer,
        customer=payer,
        idempotency_key=idempotency_key,
        requires_otp=True,
        otp_verified_at=otp_req.verified_at,
    )

    # Mark the QR code as paid
    QRPayment.objects.filter(pk=qr.pk).update(
        status=QRPaymentStatus.PAID,
        transaction=transaction,
        payer_account=payer_account,
    )

    logger.info(
        "QR payment completed | ref=%s token=%s amount=%s",
        transaction.reference_number,
        qr_token[:12],
        pay_amount,
    )
    return transaction


# ---------------------------------------------------------------------------
# Bill Payment
# ---------------------------------------------------------------------------

def send_bill_payment_otp(
    *,
    user,
    provider_code: str,
    service_number: str,
    ip: str = "",
    device_id: str = "",
) -> str:
    """Issue an OTP scoped to a specific bill (provider+service used as purpose_ref). Returns plaintext OTP."""
    purpose_ref = f"{provider_code}:{service_number}"
    _, otp_plain = create_otp(
        phone=user.phone_number,
        request_type=OTPRequestType.BILL_PAYMENT,
        purpose_ref=purpose_ref,
        ip=ip,
        device_id=device_id,
        user=user,
    )
    return otp_plain


def fetch_bill_info(
    *,
    provider_code: str,
    service_number: str,
) -> dict:
    """
    Fetch bill information for a given service number.

    In production this would call an external biller API.
    Here we return a deterministic mock response for development/testing.
    """
    try:
        provider = BillProvider.objects.get(code=provider_code)
    except BillProvider.DoesNotExist:
        raise BillProviderNotFoundError(
            f"Bill provider '{provider_code}' not found."
        )

    if not provider.is_active:
        raise BillProviderNotActiveError(
            f"Bill provider '{provider_code}' is not currently active."
        )

    # Deterministic mock: amount is derived from last 4 digits of service_number
    try:
        mock_amount = Decimal(str(int(service_number[-4:]) % 1000 + 50))
    except (ValueError, IndexError):
        mock_amount = Decimal("100.00")

    return {
        "provider_code": provider.code,
        "provider_name": provider.name,
        "service_type": provider.service_type,
        "service_number": service_number,
        "bill_reference": f"BILL-{provider_code}-{service_number[-6:]}",
        "amount": str(mock_amount),
        "currency": "USD",
        "fetched_at": timezone.now().isoformat(),
    }


def process_bill_payment(
    *,
    customer,
    payer_account: Account,
    provider_code: str,
    service_number: str,
    bill_reference: str,
    amount: Decimal,
    otp_code: str,
    idempotency_key: str | None = None,
    channel: str = TransactionChannel.MOBILE,
) -> "Transaction":  # noqa: F821
    """
    Execute a bill payment.

    Flow:
      1. Resolve provider.
      2. Verify BILL_PAYMENT OTP scoped to provider+service_number.
      3. post_transaction(BILL_PAYMENT, payer → provider_account).
      4. Write BillPayment satellite record.
    """
    try:
        provider = BillProvider.objects.get(code=provider_code, is_active=True)
    except BillProvider.DoesNotExist:
        raise BillProviderNotFoundError(
            f"Active bill provider '{provider_code}' not found."
        )

    purpose_ref = f"{provider_code}:{service_number}"
    otp_req = verify_otp(
        phone=customer.phone_number,
        request_type=OTPRequestType.BILL_PAYMENT,
        otp_plain=otp_code,
        purpose_ref=purpose_ref,
    )

    transaction = post_transaction(
        transaction_type=TransactionType.BILL_PAYMENT,
        currency_code="USD",
        amount=Decimal(str(amount)),
        source_account=payer_account,
        destination_account=provider.provider_account,
        description=f"Bill payment: {provider.name} / {service_number}",
        channel=channel,
        initiated_by=customer,
        customer=customer,
        idempotency_key=idempotency_key,
        requires_otp=True,
        otp_verified_at=otp_req.verified_at,
    )

    BillPayment.objects.create(
        transaction=transaction,
        bill_provider=provider,
        payer_account=payer_account,
        service_number=service_number,
        bill_reference=bill_reference,
        biller_amount=Decimal(str(amount)),
        fetched_at=timezone.now(),
        paid_at=timezone.now(),
    )

    logger.info(
        "Bill payment completed | ref=%s provider=%s service=%s amount=%s",
        transaction.reference_number,
        provider_code,
        service_number,
        amount,
    )
    return transaction
