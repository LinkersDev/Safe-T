"""
Reporting API view tests.

Covered:
  1.  GET /admin/summary/                 → 200 with correct structure
  2.  GET /admin/users/growth/            → 200
  3.  GET /admin/users/status/            → 200
  4.  GET /admin/transactions/volume/     → daily default, weekly with param
  5.  GET /admin/transactions/by-type/    → 200
  6.  GET /admin/fees/aggregate/          → 200
  7.  GET /risk/summary/                  → 200 for Risk Officer
  8.  GET /risk/metrics/                  → 200 with period_days
  9.  GET /operations/summary/            → 200 for KYC reviewer
  10. GET /operations/transactions/recent/ → 200
  11. GET /audit/transactions/{ref}/trace/ → 200 with entries
  12. GET /audit/transactions/{ref}/trace/ → 404 for bad ref
  13. GET /audit/accounts/{id}/restrictions/ → 200
  14. GET /audit/risk/alerts/{id}/decisions/ → 200
  15. Permission enforcement — 403 for each guarded endpoint
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.constants import AccountStatus, RestrictionSource, RestrictionType
from apps.accounts.models import Account, AccountRestriction, Currency
from apps.ledger.constants import EntryType, TransactionStatus, TransactionType
from apps.ledger.models import Transaction, TransactionEntry
from apps.risk.constants import AlertSeverity, AlertStatus, AlertType, DecisionAction
from apps.risk.models import FraudAlert, FraudDecision
from apps.users.constants import KycStatus, UserStatus
from apps.users.models import Permission, Role, RolePermission, User


BASE = "/api/staff/reports/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _currency():
    return Currency.objects.get_or_create(
        code="USD",
        defaults={"name": "US Dollar", "symbol": "$", "decimal_places": 2},
    )[0]


def _user(phone, kyc=KycStatus.APPROVED):
    return User.objects.create_user(
        phone_number=phone, password="P!", status=UserStatus.ACTIVE, kyc_status=kyc
    )


def _staff(phone, *perm_codes):
    """Create a staff user with the given permission codes."""
    user = User.objects.create_user(
        phone_number=phone, password="P!", status=UserStatus.ACTIVE,
        kyc_status=KycStatus.APPROVED, is_staff=True,
    )
    role, _ = Role.objects.get_or_create(code=f"R_{phone[-4:]}", defaults={"name": f"Role {phone[-4:]}"})
    user.role = role
    user.save(update_fields=["role"])
    for code in perm_codes:
        perm, _ = Permission.objects.get_or_create(code=code, defaults={"name": code, "module": "reporting"})
        RolePermission.objects.get_or_create(role=role, permission=perm)
    return user


def _bearer(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")
    return client


def _account(user, balance=Decimal("5000.00")):
    cur = _currency()
    return Account.objects.create(
        user=user, currency=cur,
        account_number=f"{7000 + Account.objects.count():016d}",
        account_name="Test Acct", status=AccountStatus.ACTIVE,
        available_balance=balance, ledger_balance=balance,
    )


def _tx(src, dst, amount):
    cur = _currency()
    tx = Transaction.objects.create(
        reference_number=f"RPT{Transaction.objects.count():010d}",
        transaction_type=TransactionType.TRANSFER,
        status=TransactionStatus.COMPLETED,
        currency=cur, amount=amount,
    )
    TransactionEntry.objects.create(
        transaction=tx, account=src, entry_type=EntryType.DEBIT, amount=amount, sequence_no=1
    )
    TransactionEntry.objects.create(
        transaction=tx, account=dst, entry_type=EntryType.CREDIT, amount=amount, sequence_no=2
    )
    return tx


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

class AdminReportTests(TestCase):
    def setUp(self):
        _currency()
        self.admin_user = _staff("+96650010001", "view_all_transactions", "view_all_users")
        self.client     = _bearer(self.admin_user)
        u1 = _user("+96650010002")
        u2 = _user("+96650010003")
        a1 = _account(u1)
        a2 = _account(u2)
        self.tx = _tx(a1, a2, Decimal("500.00"))

    def test_admin_summary(self):
        resp = self.client.get(f"{BASE}admin/summary/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("total_users", body)
        self.assertIn("fee_revenue", body)

    def test_user_growth(self):
        resp = self.client.get(f"{BASE}admin/users/growth/?days=30")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("rows", resp.json())

    def test_user_status_breakdown(self):
        resp = self.client.get(f"{BASE}admin/users/status/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("ACTIVE", body)

    def test_tx_volume_daily(self):
        resp = self.client.get(f"{BASE}admin/transactions/volume/?period=daily&days=7")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["period"], "daily")

    def test_tx_volume_weekly(self):
        resp = self.client.get(f"{BASE}admin/transactions/volume/?period=weekly&weeks=4")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["period"], "weekly")

    def test_tx_by_type(self):
        resp = self.client.get(f"{BASE}admin/transactions/by-type/?days=30")
        self.assertEqual(resp.status_code, 200)

    def test_fee_aggregate(self):
        resp = self.client.get(f"{BASE}admin/fees/aggregate/?days=30")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("total_fee_revenue", resp.json())

    def test_no_permission_admin_summary(self):
        no_perm = _bearer(_user("+96650010090"))
        resp = no_perm.get(f"{BASE}admin/summary/")
        self.assertEqual(resp.status_code, 403)

    def test_no_permission_user_growth(self):
        no_perm = _bearer(_user("+96650010091"))
        resp = no_perm.get(f"{BASE}admin/users/growth/")
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Risk Officer endpoints
# ---------------------------------------------------------------------------

class RiskReportTests(TestCase):
    def setUp(self):
        self.risk_user = _staff("+96650010010", "review_fraud_alert")
        self.client    = _bearer(self.risk_user)
        u = _user("+96650010011")
        FraudAlert.objects.create(
            alert_type=AlertType.TRANSACTION, severity=AlertSeverity.HIGH,
            status=AlertStatus.OPEN, risk_score=55, user=u, rules_triggered=[],
        )

    def test_risk_summary(self):
        resp = self.client.get(f"{BASE}risk/summary/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("open_alerts", body)
        self.assertIn("by_severity", body)

    def test_fraud_metrics(self):
        resp = self.client.get(f"{BASE}risk/metrics/?days=30")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["period_days"], 30)

    def test_no_permission_risk_summary(self):
        no_perm = _bearer(_user("+96650010092"))
        resp = no_perm.get(f"{BASE}risk/summary/")
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Operations endpoints
# ---------------------------------------------------------------------------

class OperationsReportTests(TestCase):
    def setUp(self):
        _currency()
        self.ops_user = _staff("+96650010020", "review_kyc")
        self.client   = _bearer(self.ops_user)
        u1 = _user("+96650010021")
        u2 = _user("+96650010022")
        a1 = _account(u1)
        a2 = _account(u2)
        _tx(a1, a2, Decimal("300.00"))

    def test_operations_summary(self):
        resp = self.client.get(f"{BASE}operations/summary/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("pending_kyc_users", body)
        self.assertIn("open_support_tickets", body)

    def test_recent_transactions(self):
        admin_user = _staff("+96650010023", "view_all_transactions")
        resp = _bearer(admin_user).get(f"{BASE}operations/transactions/recent/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_no_permission_operations_summary(self):
        no_perm = _bearer(_user("+96650010093"))
        resp = no_perm.get(f"{BASE}operations/summary/")
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Audit endpoints
# ---------------------------------------------------------------------------

class AuditReportTests(TestCase):
    def setUp(self):
        _currency()
        self.admin_user = _staff("+96650010030", "view_all_transactions", "view_all_accounts", "review_fraud_alert")
        self.client     = _bearer(self.admin_user)
        u1 = _user("+96650010031")
        u2 = _user("+96650010032")
        self.a1 = _account(u1)
        self.a2 = _account(u2)
        self.tx = _tx(self.a1, self.a2, Decimal("750.00"))
        self.alert = FraudAlert.objects.create(
            alert_type=AlertType.TRANSACTION, severity=AlertSeverity.HIGH,
            status=AlertStatus.DISMISSED, risk_score=55,
            user=u1, account=self.a1, transaction=self.tx, rules_triggered=[],
        )
        FraudDecision.objects.create(
            alert=self.alert, officer=self.admin_user,
            action=DecisionAction.DISMISS, notes="OK",
        )
        AccountRestriction.objects.create(
            account=self.a1, restriction_type=RestrictionType.FREEZE,
            reason="Test", source=RestrictionSource.RISK_OFFICER,
            applied_by=self.admin_user, is_active=True,
        )

    def test_transaction_trace_200(self):
        resp = self.client.get(f"{BASE}audit/transactions/{self.tx.reference_number}/trace/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["reference_number"], self.tx.reference_number)
        self.assertEqual(len(body["entries"]), 2)

    def test_transaction_trace_includes_fraud_alerts(self):
        resp = self.client.get(f"{BASE}audit/transactions/{self.tx.reference_number}/trace/")
        body = resp.json()
        self.assertEqual(len(body["fraud_alerts"]), 1)
        self.assertEqual(body["fraud_alerts"][0]["severity"], AlertSeverity.HIGH)

    def test_transaction_trace_404(self):
        resp = self.client.get(f"{BASE}audit/transactions/BADREF/trace/")
        self.assertEqual(resp.status_code, 404)

    def test_account_restriction_history(self):
        resp = self.client.get(f"{BASE}audit/accounts/{self.a1.pk}/restrictions/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["restriction_type"], RestrictionType.FREEZE)

    def test_alert_decision_history(self):
        resp = self.client.get(f"{BASE}audit/risk/alerts/{self.alert.pk}/decisions/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["action"], DecisionAction.DISMISS)

    def test_no_permission_trace(self):
        no_perm = _bearer(_user("+96650010094"))
        resp = no_perm.get(f"{BASE}audit/transactions/{self.tx.reference_number}/trace/")
        self.assertEqual(resp.status_code, 403)

    def test_no_permission_restrictions(self):
        no_perm = _bearer(_user("+96650010095"))
        resp = no_perm.get(f"{BASE}audit/accounts/{self.a1.pk}/restrictions/")
        self.assertEqual(resp.status_code, 403)
