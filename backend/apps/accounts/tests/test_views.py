"""
Integration tests for accounts views.

Run:
    python manage.py test apps.accounts.tests.test_views \
        --settings=config.settings.test --verbosity=2
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.constants import RoleCode, UserStatus
from apps.users.models import Permission, Role, RolePermission, User

from apps.accounts.constants import AccountStatus
from apps.accounts.models import Account, Currency
from apps.accounts.services import create_account, freeze_account, block_account


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_role(code, is_staff=False):
    role, _ = Role.objects.get_or_create(
        code=code,
        defaults={"name": code.title(), "is_staff_role": is_staff, "is_system_role": True},
    )
    return role


def _make_active_user(phone="+966501200001"):
    role = _make_role(RoleCode.CUSTOMER)
    user = User(
        phone_number=phone,
        phone_number_normalized=phone,
        full_name="View Tester",
        role=role,
        status=UserStatus.ACTIVE,
        is_active=True,
    )
    user.set_password("TestPass1!")
    user.save()
    return user


def _make_staff_user(phone="+966501200050", role_code=RoleCode.ADMIN, perms=None):
    role = _make_role(role_code, is_staff=True)
    user = User(
        phone_number=phone,
        phone_number_normalized=phone,
        full_name="Staff User",
        role=role,
        status=UserStatus.ACTIVE,
        is_active=True,
        is_staff=True,
    )
    user.set_password("StaffPass1!")
    user.save()
    if perms:
        for perm_code in perms:
            perm, _ = Permission.objects.get_or_create(
                code=perm_code,
                defaults={"name": perm_code, "module": "accounts"},
            )
            RolePermission.objects.get_or_create(role=role, permission=perm)
    return user


# ===========================================================================
# Customer account views
# ===========================================================================

class AccountListViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = _make_active_user("+966501200010")
        self.account = create_account(user=self.user)

    def test_authenticated_user_sees_own_accounts(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse("account-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["account_number"], self.account.account_number)

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(reverse("account-list"))
        self.assertEqual(resp.status_code, 401)

    def test_pending_user_cannot_list_accounts(self):
        pending = _make_active_user("+966501200011")
        pending.status = UserStatus.PENDING_VERIFICATION
        pending.save()
        self.client.force_authenticate(user=pending)
        resp = self.client.get(reverse("account-list"))
        self.assertEqual(resp.status_code, 403)

    def test_user_does_not_see_other_users_accounts(self):
        other = _make_active_user("+966501200012")
        create_account(user=other)
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse("account-list"))
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["account_number"], self.account.account_number)


class AccountDetailViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = _make_active_user("+966501200020")
        self.account = create_account(user=self.user)

    def test_owner_can_retrieve_account(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse("account-detail", kwargs={"account_id": self.account.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("account_number", resp.data)
        self.assertIn("available_balance", resp.data)

    def test_non_owner_gets_403(self):
        other = _make_active_user("+966501200021")
        self.client.force_authenticate(user=other)
        resp = self.client.get(reverse("account-detail", kwargs={"account_id": self.account.pk}))
        self.assertEqual(resp.status_code, 403)

    def test_missing_account_returns_404(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse("account-detail", kwargs={"account_id": 9999}))
        self.assertEqual(resp.status_code, 404)


# ===========================================================================
# Beneficiary views
# ===========================================================================

class BeneficiaryViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = _make_active_user("+966501200030")
        self.other_user = _make_active_user("+966501200031")
        self.dest_account = create_account(user=self.other_user)

    def test_add_beneficiary_returns_201(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(reverse("beneficiary-list-create"), {
            "account_number": self.dest_account.account_number,
            "nickname": "My Friend",
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertIn("destination_account_number", resp.data)

    def test_list_beneficiaries_returns_200(self):
        from apps.accounts.services import add_beneficiary
        add_beneficiary(
            owner=self.user,
            destination_account=self.dest_account,
            nickname="Test",
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse("beneficiary-list-create"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_cannot_add_own_account_as_beneficiary(self):
        own_account = create_account(user=self.user)
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(reverse("beneficiary-list-create"), {
            "account_number": own_account.account_number,
            "nickname": "Myself",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "own_account")

    def test_invalid_account_number_returns_400(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(reverse("beneficiary-list-create"), {
            "account_number": "not-a-number",
            "nickname": "Test",
        })
        self.assertEqual(resp.status_code, 400)

    def test_nonexistent_account_returns_404(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(reverse("beneficiary-list-create"), {
            "account_number": "1234567890123456",
            "nickname": "Nobody",
        })
        self.assertEqual(resp.status_code, 404)

    def test_remove_beneficiary_returns_204(self):
        from apps.accounts.services import add_beneficiary
        b = add_beneficiary(
            owner=self.user,
            destination_account=self.dest_account,
            nickname="Test",
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.delete(
            reverse("beneficiary-remove", kwargs={"beneficiary_id": b.pk})
        )
        self.assertEqual(resp.status_code, 204)


# ===========================================================================
# Staff account management views
# ===========================================================================

class StaffAccountViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = _make_active_user("+966501200040")
        self.account = create_account(user=self.customer)
        self.staff = _make_staff_user(
            "+966501200051",
            RoleCode.RISK_OFFICER,
            perms=["freeze_account", "unfreeze_account", "block_account", "view_all_accounts"],
        )

    def test_freeze_returns_200(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post(
            reverse("staff-account-freeze", kwargs={"account_id": self.account.pk}),
            {"reason": "Suspected fraud on account"},
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.FROZEN)

    def test_unfreeze_returns_200(self):
        freeze_account(account=self.account, reason="Test")
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post(
            reverse("staff-account-unfreeze", kwargs={"account_id": self.account.pk}),
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.ACTIVE)

    def test_block_returns_200(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post(
            reverse("staff-account-block", kwargs={"account_id": self.account.pk}),
            {"reason": "Confirmed fraud investigation"},
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.BLOCKED)

    def test_unblock_returns_200(self):
        block_account(account=self.account, reason="Test block")
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post(
            reverse("staff-account-unblock", kwargs={"account_id": self.account.pk}),
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.ACTIVE)

    def test_close_returns_200(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post(
            reverse("staff-account-close", kwargs={"account_id": self.account.pk}),
            {"reason": "Customer closure request"},
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.CLOSED)

    def test_freeze_missing_reason_returns_400(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post(
            reverse("staff-account-freeze", kwargs={"account_id": self.account.pk}),
            {},
        )
        self.assertEqual(resp.status_code, 400)

    def test_staff_without_permission_gets_403(self):
        no_perm_staff = _make_staff_user("+966501200052", RoleCode.TELLER, perms=[])
        self.client.force_authenticate(user=no_perm_staff)
        resp = self.client.post(
            reverse("staff-account-freeze", kwargs={"account_id": self.account.pk}),
            {"reason": "Unauthorized attempt"},
        )
        self.assertEqual(resp.status_code, 403)
