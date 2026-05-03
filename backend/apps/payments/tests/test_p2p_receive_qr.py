"""Tests for customer peer receive QR issue + resolve endpoints."""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.constants import AccountStatus
from apps.accounts.models import Account, Currency
from apps.users.constants import KycStatus, RoleCode, UserStatus
from apps.users.models import Role, User


def _currency():
    return Currency.objects.get_or_create(
        code="USD",
        defaults={"name": "US Dollar", "symbol": "$", "decimal_places": 2},
    )[0]


def _customer(phone: str, *, full_name: str = "Peer User"):
    role, _ = Role.objects.get_or_create(
        code=RoleCode.CUSTOMER,
        defaults={"name": "Customer"},
    )
    return User.objects.create_user(
        phone_number=phone,
        password="TestPass1!",
        full_name=full_name,
        status=UserStatus.ACTIVE,
        kyc_status=KycStatus.APPROVED,
        role=role,
    )


def _account(owner: User) -> Account:
    _currency()
    return Account.objects.create(
        user=owner,
        currency=Currency.objects.get(code="USD"),
        account_number=f"{9000 + Account.objects.count():016d}",
        account_name=f"Acct {owner.phone_number}",
        status=AccountStatus.ACTIVE,
        available_balance=Decimal("500.00"),
        ledger_balance=Decimal("500.00"),
    )


def _auth(user: User) -> APIClient:
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


class P2PReceiveQrIssueResolveTest(TestCase):
    def setUp(self):
        self.alice = _customer("+966500009901")
        self.bob = _customer("+966500009902")
        self.acc_alice = _account(self.alice)
        _account(self.bob)

        self.client_alice = _auth(self.alice)
        self.client_bob = _auth(self.bob)

    def test_issue_returns_prefixed_payload(self):
        resp = self.client_alice.post("/api/payments/p2p-receive-qr/issue/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        payload = resp.data["qr_payload"]
        self.assertTrue(payload.startswith("safet:p2p:v1:"))
        self.assertIn("expires_in_seconds", resp.data)

    def test_resolve_returns_fresh_identity_for_scanner(self):
        resp_issue = self.client_alice.post("/api/payments/p2p-receive-qr/issue/", {}, format="json")
        payload = resp_issue.data["qr_payload"]

        resp_resolve = self.client_bob.get(
            "/api/payments/p2p-receive-qr/resolve/",
            {"payload": payload},
        )
        self.assertEqual(resp_resolve.status_code, 200)
        self.assertEqual(resp_resolve.data["full_name"], self.alice.full_name)
        self.assertEqual(resp_resolve.data["phone_number"], self.alice.phone_number)
        self.assertEqual(resp_resolve.data["account_number"], self.acc_alice.account_number)

    def test_issue_fails_without_active_account(self):
        lone = _customer("+966500009903")
        client = _auth(lone)
        resp = client.post("/api/payments/p2p-receive-qr/issue/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
