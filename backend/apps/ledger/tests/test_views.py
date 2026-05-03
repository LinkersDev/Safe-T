"""Integration tests for ledger API views."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.constants import AccountStatus
from apps.accounts.models import Account, Currency
from apps.users.constants import UserStatus
from apps.users.models import Role, User

from ..constants import TransactionStatus, TransactionType
from ..services import post_transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _currency():
    return Currency.objects.get_or_create(
        code="USD",
        defaults={"name": "US Dollar", "symbol": "﷼", "decimal_places": 2},
    )[0]


def _user(phone: str = "+966500000100", status: str = UserStatus.ACTIVE):
    from apps.users.constants import KycStatus
    return User.objects.create_user(
        phone_number=phone,
        password="TestPass1!",
        status=status,
        kyc_status=KycStatus.APPROVED,
    )


def _account(owner: User, balance: Decimal = Decimal("1000.00")):
    _currency()
    acc = Account.objects.create(
        user=owner,
        currency=Currency.objects.get(code="USD"),
        account_number=f"{9000 + Account.objects.count():016d}",
        account_name=f"Account {owner.phone_number}",
        status=AccountStatus.ACTIVE,
        available_balance=balance,
        ledger_balance=balance,
    )
    return acc


def _staff_user(phone: str = "+966500000199"):
    role, _ = Role.objects.get_or_create(name="ADMIN")
    from apps.users.models import Permission, RolePermission
    for perm_code in ["view_all_transactions", "reverse_transaction", "manage_system"]:
        perm, _ = Permission.objects.get_or_create(
            code=perm_code,
            defaults={"name": perm_code.replace("_", " ").title()},
        )
        RolePermission.objects.get_or_create(role=role, permission=perm)
    user = User.objects.create_user(
        phone_number=phone,
        password="StaffPass1!",
        status=UserStatus.ACTIVE,
    )
    user.role = role
    user.save(update_fields=["role"])
    return user


def _auth_client(user: User) -> APIClient:
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


# ---------------------------------------------------------------------------
# Customer view tests
# ---------------------------------------------------------------------------

class TransactionListViewTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.user = _user("+966500000101")
        self.other_user = _user("+966500000102")
        self.source = _account(self.user, Decimal("2000.00"))
        self.dest = _account(self.other_user, Decimal("0.00"))
        self.client_auth = _auth_client(self.user)

        self.tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("100.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.user,
        )

    def test_customer_sees_own_transactions(self):
        response = self.client_auth.get("/api/ledger/transactions/")
        self.assertEqual(response.status_code, 200)
        refs = [t["reference_number"] for t in response.data]
        self.assertIn(self.tx.reference_number, refs)

    def test_unauthenticated_denied(self):
        response = APIClient().get("/api/ledger/transactions/")
        self.assertEqual(response.status_code, 401)

    def test_pending_user_denied(self):
        pending = _user("+966500000103", status=UserStatus.PENDING_VERIFICATION)
        client = _auth_client(pending)
        response = client.get("/api/ledger/transactions/")
        self.assertEqual(response.status_code, 403)


class TransactionDetailViewTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.user = _user("+966500000104")
        self.other = _user("+966500000105")
        self.source = _account(self.user, Decimal("500.00"))
        self.dest = _account(self.other, Decimal("0.00"))
        self.client_auth = _auth_client(self.user)
        self.tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("50.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.user,
        )

    def test_detail_returns_entries(self):
        url = f"/api/ledger/transactions/{self.tx.reference_number}/"
        response = self.client_auth.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reference_number"], self.tx.reference_number)
        self.assertIn("entries", response.data)
        self.assertEqual(len(response.data["entries"]), 2)

    def test_other_user_cannot_access(self):
        other_client = _auth_client(self.other)
        url = f"/api/ledger/transactions/{self.tx.reference_number}/"
        response = other_client.get(url)
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Staff view tests
# ---------------------------------------------------------------------------

class StaffTransactionListViewTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.customer = _user("+966500000110")
        self.staff = _staff_user("+966500000111")
        self.source = _account(self.customer, Decimal("1000.00"))
        self.dest = _account(self.staff, Decimal("0.00"))

        self.tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("200.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.customer,
        )

    def test_staff_sees_all_transactions(self):
        client = _auth_client(self.staff)
        response = client.get("/api/staff/ledger/transactions/")
        self.assertEqual(response.status_code, 200)

    def test_customer_denied_staff_list(self):
        client = _auth_client(self.customer)
        response = client.get("/api/staff/ledger/transactions/")
        self.assertEqual(response.status_code, 403)


class ReverseTransactionViewTest(TestCase):
    def setUp(self):
        self.currency = _currency()
        self.customer = _user("+966500000120")
        self.staff = _staff_user("+966500000121")
        self.source = _account(self.customer, Decimal("1000.00"))
        self.dest = _account(self.staff, Decimal("0.00"))
        self.tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("250.00"),
            source_account=self.source,
            destination_account=self.dest,
            customer=self.customer,
        )

    def test_staff_can_reverse(self):
        client = _auth_client(self.staff)
        url = f"/api/staff/ledger/transactions/{self.tx.reference_number}/reverse/"
        response = client.post(url, {"reason": "Test reversal"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("reference_number", response.data)

    def test_customer_cannot_reverse(self):
        client = _auth_client(self.customer)
        url = f"/api/staff/ledger/transactions/{self.tx.reference_number}/reverse/"
        response = client.post(url, {"reason": "Attempt"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_double_reversal_returns_409(self):
        client = _auth_client(self.staff)
        url = f"/api/staff/ledger/transactions/{self.tx.reference_number}/reverse/"
        client.post(url, {"reason": "First"}, format="json")
        response = client.post(url, {"reason": "Second"}, format="json")
        self.assertEqual(response.status_code, 409)

    def test_missing_reason_returns_400(self):
        client = _auth_client(self.staff)
        url = f"/api/staff/ledger/transactions/{self.tx.reference_number}/reverse/"
        response = client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_not_found_returns_404(self):
        client = _auth_client(self.staff)
        url = "/api/staff/ledger/transactions/TRFNONEXISTENT/reverse/"
        response = client.post(url, {"reason": "Test"}, format="json")
        self.assertEqual(response.status_code, 404)
