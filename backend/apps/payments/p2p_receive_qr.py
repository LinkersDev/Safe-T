"""
Signed short-lived payloads for customer-to-customer receive QR codes.

The QR encodes a prefix plus Django-signed blob binding user_id + account_id.
Resolve reloads fresh phone/account/name from the DB after signature verification.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core import signing

from apps.accounts.constants import AccountStatus
from apps.accounts.selectors import get_accounts_for_user
from apps.users.constants import RoleCode

User = get_user_model()

P2P_QR_PREFIX = "safet:p2p:v1:"
SIGNING_SALT = "safet.p2p.receive_qr.v1"
MAX_AGE_SECONDS = 3600


class P2PReceiveQrError(Exception):
    """Invalid, expired, or inconsistent receive QR payload."""


def _is_customer_like_role(user) -> bool:
    role = getattr(user, "role", None)
    code = getattr(role, "code", None) if role else None
    return code in (RoleCode.CUSTOMER, RoleCode.MERCHANT_CUSTOMER)


def _pick_display_account(user):
    qs = get_accounts_for_user(user).filter(status=AccountStatus.ACTIVE)
    usd = qs.filter(currency_id="USD").first()
    return usd or qs.first()


def issue_receive_qr_string(user) -> tuple[str, int]:
    """
    Build full QR string for the authenticated customer.

    Returns (qr_string, max_age_seconds).
    Raises P2PReceiveQrError if user cannot issue or has no active account.
    """
    if not _is_customer_like_role(user):
        raise P2PReceiveQrError("Only customer accounts can issue receive QR codes.")

    account = _pick_display_account(user)
    if account is None:
        raise P2PReceiveQrError("No active account available for receive QR.")

    blob = signing.dumps(
        {"v": 1, "uid": user.pk, "acc_id": account.pk},
        salt=SIGNING_SALT,
    )
    return f"{P2P_QR_PREFIX}{blob}", MAX_AGE_SECONDS


def resolve_receive_qr_string(raw: str) -> dict:
    """
    Validate QR contents and return payer-facing recipient preview.

    Expected format: safet:p2p:v1:<signed_blob>
    Raises P2PReceiveQrError on failure.
    """
    text = (raw or "").strip()
    if text.startswith(P2P_QR_PREFIX):
        blob = text[len(P2P_QR_PREFIX) :].strip()
    else:
        blob = text

    if not blob:
        raise P2PReceiveQrError("Missing QR payload.")

    try:
        data = signing.loads(blob, salt=SIGNING_SALT, max_age=MAX_AGE_SECONDS)
    except signing.SignatureExpired as exc:
        raise P2PReceiveQrError("This receive QR has expired. Ask the recipient for a new one.") from exc
    except signing.BadSignature as exc:
        raise P2PReceiveQrError("Invalid QR code.") from exc

    if not isinstance(data, dict) or data.get("v") != 1:
        raise P2PReceiveQrError("Unsupported QR format.")

    try:
        uid = int(data["uid"])
        acc_id = int(data["acc_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise P2PReceiveQrError("Invalid QR payload.") from exc

    try:
        recipient = User.objects.select_related("role").get(pk=uid)
    except User.DoesNotExist as exc:
        raise P2PReceiveQrError("Recipient not found.") from exc

    if not _is_customer_like_role(recipient):
        raise P2PReceiveQrError("Recipient is not eligible for peer payments.")

    from apps.accounts.models import Account

    try:
        account = Account.objects.select_related("currency").get(pk=acc_id, user_id=uid)
    except Account.DoesNotExist as exc:
        raise P2PReceiveQrError("Recipient account not found.") from exc

    if account.status != AccountStatus.ACTIVE:
        raise P2PReceiveQrError("Recipient account is not active.")

    phone = (recipient.phone_number or "").strip()
    return {
        "full_name": recipient.full_name,
        "phone_number": phone,
        "account_number": account.account_number,
        "currency_code": account.currency_id,
    }
