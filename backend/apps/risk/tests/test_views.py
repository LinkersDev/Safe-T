"""
Integration tests for risk API endpoints.

Covered:
  1. GET  /api/staff/risk/alerts/ → lists alerts (filter by status, severity)
  2. GET  /api/staff/risk/alerts/{id}/ → alert detail with decision
  3. POST /api/staff/risk/alerts/{id}/review/ → Risk Officer submits decision
  4. POST /api/staff/risk/alerts/{id}/dismiss/ → shortcut dismiss
  5. Staff permission enforcement (review_fraud_alert required)
  6. Double review returns 409
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.constants import AccountStatus
from apps.accounts.models import Account, Currency
from apps.users.constants import KycStatus, UserStatus
from apps.users.models import Permission, Role, RolePermission, User

from apps.risk.constants import AlertSeverity, AlertStatus, AlertType, DecisionAction
from apps.risk.models import FraudAlert


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _currency():
    return Currency.objects.get_or_create(
        code="USD", defaults={"name": "US Dollar", "symbol": "$", "decimal_places": 2}
    )[0]


def _user(phone, kyc=KycStatus.APPROVED):
    return User.objects.create_user(
        phone_number=phone, password="Pass1!", status=UserStatus.ACTIVE, kyc_status=kyc
    )


def _risk_officer(phone="+966599903001"):
    role, _ = Role.objects.get_or_create(code="RISK_OFFICER", defaults={"name": "Risk Officer"})
    perm, _ = Permission.objects.get_or_create(
        code="review_fraud_alert", defaults={"name": "Review Fraud Alert"}
    )
    RolePermission.objects.get_or_create(role=role, permission=perm)
    user = User.objects.create_user(
        phone_number=phone, password="StaffPass1!", status=UserStatus.ACTIVE,
        kyc_status=KycStatus.APPROVED,
    )
    user.role = role
    user.save(update_fields=["role"])
    return user


def _bearer(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")
    return client


def _account(user):
    return Account.objects.create(
        user=user, currency=_currency(),
        account_number=f"{9000 + Account.objects.count():016d}",
        account_name=f"Acct {user.phone_number}",
        status=AccountStatus.ACTIVE,
        available_balance=Decimal("10000.00"),
        ledger_balance=Decimal("10000.00"),
    )


def _alert(user, account=None, severity=AlertSeverity.HIGH, status=AlertStatus.OPEN):
    return FraudAlert.objects.create(
        alert_type=AlertType.TRANSACTION,
        severity=severity,
        status=status,
        risk_score=55 if severity == AlertSeverity.HIGH else 75,
        user=user,
        account=account,
        rules_triggered=["High-value transaction: 5000"],
    )


# ---------------------------------------------------------------------------
# Alert list / detail
# ---------------------------------------------------------------------------

class AlertListDetailTest(TestCase):

    def setUp(self):
        self.officer = _risk_officer()
        self.client  = _bearer(self.officer)
        self.subject = _user("+966500060001")
        _alert(self.subject, severity=AlertSeverity.HIGH)
        _alert(self.subject, severity=AlertSeverity.CRITICAL)

    def test_list_all_alerts(self):
        resp = self.client.get("/api/staff/risk/alerts/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_filter_by_severity(self):
        resp = self.client.get("/api/staff/risk/alerts/?severity=CRITICAL")
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["severity"], AlertSeverity.CRITICAL)

    def test_filter_by_status(self):
        resp = self.client.get("/api/staff/risk/alerts/?status=OPEN")
        self.assertEqual(len(resp.json()), 2)

    def test_alert_detail(self):
        alert = FraudAlert.objects.first()
        resp = self.client.get(f"/api/staff/risk/alerts/{alert.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("rules_triggered", resp.json())
        self.assertIn("decision", resp.json())

    def test_no_permission_blocked(self):
        no_perm = User.objects.create_user(
            phone_number="+966599999002", password="P!", status=UserStatus.ACTIVE,
            kyc_status=KycStatus.APPROVED,
        )
        client = _bearer(no_perm)
        resp = client.get("/api/staff/risk/alerts/")
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Review / dismiss
# ---------------------------------------------------------------------------

class AlertReviewTest(TestCase):

    def setUp(self):
        self.officer = _risk_officer()
        self.client  = _bearer(self.officer)
        self.subject = _user("+966500060010")
        self.account = _account(self.subject)
        self.alert   = _alert(self.subject, account=self.account)

    def test_dismiss_via_review(self):
        resp = self.client.post(
            f"/api/staff/risk/alerts/{self.alert.pk}/review/",
            {"action": DecisionAction.DISMISS, "notes": "False positive."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], AlertStatus.DISMISSED)

    def test_freeze_account_via_review(self):
        resp = self.client.post(
            f"/api/staff/risk/alerts/{self.alert.pk}/review/",
            {"action": DecisionAction.FREEZE_ACCOUNT, "notes": "Suspicious."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.FROZEN)

    def test_block_account_via_review(self):
        resp = self.client.post(
            f"/api/staff/risk/alerts/{self.alert.pk}/review/",
            {"action": DecisionAction.BLOCK_ACCOUNT},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.BLOCKED)

    def test_invalid_action_rejected(self):
        resp = self.client.post(
            f"/api/staff/risk/alerts/{self.alert.pk}/review/",
            {"action": "NUKE_EVERYTHING"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_double_review_returns_409(self):
        self.client.post(
            f"/api/staff/risk/alerts/{self.alert.pk}/review/",
            {"action": DecisionAction.DISMISS},
            format="json",
        )
        resp = self.client.post(
            f"/api/staff/risk/alerts/{self.alert.pk}/review/",
            {"action": DecisionAction.WARN},
            format="json",
        )
        self.assertEqual(resp.status_code, 409)

    def test_dismiss_shortcut(self):
        resp = self.client.post(f"/api/staff/risk/alerts/{self.alert.pk}/dismiss/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], AlertStatus.DISMISSED)

    def test_decision_appears_in_detail(self):
        self.client.post(
            f"/api/staff/risk/alerts/{self.alert.pk}/review/",
            {"action": DecisionAction.WARN, "notes": "Monitor this user."},
            format="json",
        )
        resp = self.client.get(f"/api/staff/risk/alerts/{self.alert.pk}/")
        decision = resp.json()["decision"]
        self.assertIsNotNone(decision)
        self.assertEqual(decision["action"], DecisionAction.WARN)
        self.assertEqual(decision["notes"], "Monitor this user.")
