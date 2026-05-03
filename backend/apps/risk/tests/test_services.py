"""
Risk engine service tests.

Covered:
  1.  score_transaction — LOW (no alert for small amounts)
  2.  score_transaction — MEDIUM alert (USD 5,000)
  3.  score_transaction — HIGH alert (USD 5,000 + velocity)
  4.  score_transaction — CRITICAL alert + auto-freeze (USD 10,000)
  5.  score_transaction — updates Transaction.risk_score
  6.  score_login — LOW (new user, single login, known device)
  7.  score_login — HIGH alert (new device + recent failures)
  8.  score_login — CRITICAL alert (new device + 3 failures + new country)
  9.  score_login — updates LoginLog.risk_score
  10. review_alert — FREEZE_ACCOUNT action freezes the account
  11. review_alert — DISMISS sets status DISMISSED
  12. review_alert — double review raises AlertAlreadyReviewedError
  13. dismiss_alert — shortcut
  14. alert severity classification
"""
from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.accounts.constants import AccountStatus
from apps.accounts.models import Account, Currency
from apps.ledger.constants import TransactionType, TransactionStatus
from apps.ledger.models import Transaction, TransactionEntry
from apps.ledger.constants import EntryType
from apps.security.constants import LoginStatus
from apps.security.models import LoginLog, UserDevice
from apps.users.constants import KycStatus, UserStatus
from apps.users.models import User

from apps.risk.constants import AlertSeverity, AlertStatus, AlertType, DecisionAction
from apps.risk.exceptions import AlertAlreadyReviewedError
from apps.risk.models import FraudAlert
from apps.risk.services import dismiss_alert, review_alert, score_login, score_transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _currency():
    return Currency.objects.get_or_create(
        code="USD", defaults={"name": "US Dollar", "symbol": "$", "decimal_places": 2}
    )[0]


def _user(phone="+966500050001", kyc=KycStatus.APPROVED):
    return User.objects.create_user(
        phone_number=phone, password="Pass1!", status=UserStatus.ACTIVE, kyc_status=kyc
    )


def _account(user, balance=Decimal("50000.00")):
    return Account.objects.create(
        user=user, currency=_currency(),
        account_number=f"{6000 + Account.objects.count():016d}",
        account_name=f"Acct {user.phone_number}",
        status=AccountStatus.ACTIVE,
        available_balance=balance, ledger_balance=balance,
    )


def _create_transaction(src_account, dst_account, amount, occurred_at=None) -> Transaction:
    """Create a minimal Transaction + entries directly in DB (bypasses scoring for test setup)."""
    cur = _currency()
    tx = Transaction.objects.create(
        reference_number=f"TST{Transaction.objects.count():08d}",
        transaction_type=TransactionType.TRANSFER,
        status=TransactionStatus.COMPLETED,
        currency=cur,
        amount=amount,
    )
    # auto_now_add ignores constructor kwargs; use update() to back-date occurred_at
    if occurred_at:
        Transaction.objects.filter(pk=tx.pk).update(occurred_at=occurred_at)
        tx.refresh_from_db()
    TransactionEntry.objects.create(
        transaction=tx, account=src_account,
        entry_type=EntryType.DEBIT, amount=amount, sequence_no=1,
    )
    TransactionEntry.objects.create(
        transaction=tx, account=dst_account,
        entry_type=EntryType.CREDIT, amount=amount, sequence_no=2,
    )
    return tx


def _login_log(user, phone, status=LoginStatus.SUCCESS, device_id="", country="SA", hour=12):
    log = LoginLog.objects.create(
        user=user, phone_number=phone,
        status=status, device_id=device_id,
        location_country=country,
    )
    # attempted_at is auto_now_add — backdate via update() so hour-based rules work correctly
    dt = timezone.now().replace(hour=hour, minute=0, second=0, microsecond=0)
    LoginLog.objects.filter(pk=log.pk).update(attempted_at=dt)
    log.refresh_from_db()
    return log


# ---------------------------------------------------------------------------
# Transaction scoring tests
# ---------------------------------------------------------------------------

class TransactionScoringTest(TestCase):

    def setUp(self):
        self.user = _user("+966500050001")
        self.receiver = _user("+966500050002")
        self.src_acc = _account(self.user)
        self.dst_acc = _account(self.receiver)

    def _score(self, amount, hour=12):
        dt = timezone.now().replace(hour=hour)
        tx = _create_transaction(self.src_acc, self.dst_acc, amount, occurred_at=dt)
        return tx, score_transaction(tx.pk)

    def test_low_amount_no_alert(self):
        """USD 100 → LOW → no FraudAlert created."""
        tx, alert = self._score(Decimal("100.00"))
        self.assertIsNone(alert)
        self.assertEqual(FraudAlert.objects.count(), 0)

    def test_medium_amount_alert(self):
        """USD 5,000 → score 40 → MEDIUM alert."""
        tx, alert = self._score(Decimal("5000.00"))
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, AlertSeverity.MEDIUM)
        self.assertEqual(alert.alert_type, AlertType.TRANSACTION)
        self.assertEqual(alert.status, AlertStatus.OPEN)

    def test_critical_amount_alert_and_auto_freeze(self):
        """USD 10,000 → score 75 → CRITICAL → alert + account auto-frozen."""
        tx, alert = self._score(Decimal("10000.00"))
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)
        self.assertEqual(alert.auto_action_taken, "ACCOUNT_FROZEN")
        self.assertEqual(alert.status, AlertStatus.ACTIONED)
        # Account should be FROZEN
        self.src_acc.refresh_from_db()
        self.assertEqual(self.src_acc.status, AccountStatus.FROZEN)

    def test_risk_score_written_to_transaction(self):
        """score_transaction must update Transaction.risk_score."""
        tx, _ = self._score(Decimal("5000.00"))
        tx.refresh_from_db()
        self.assertIsNotNone(tx.risk_score)
        self.assertGreater(tx.risk_score, 0)

    def test_velocity_adds_score(self):
        """5 prior debits in 1 hour push a medium-amount tx into HIGH."""
        # Create 5 prior DEBIT entries for this account
        dummy_dst = _account(_user("+966500050010"))
        for i in range(5):
            prior_tx = _create_transaction(self.src_acc, dummy_dst, Decimal("500.00"))
        # Now create the target transaction
        tx, alert = self._score(Decimal("5000.00"))  # base=40; velocity=25 → 65 HIGH
        self.assertIsNotNone(alert)
        self.assertIn(alert.severity, (AlertSeverity.HIGH, AlertSeverity.CRITICAL))

    def test_abnormal_hour_adds_score(self):
        """Transaction at 03:00 UTC adds 15 pts; USD 5,000 + hour = 55 → HIGH."""
        tx, alert = self._score(Decimal("5000.00"), hour=3)
        self.assertIsNotNone(alert)
        self.assertIn(alert.severity, (AlertSeverity.HIGH, AlertSeverity.CRITICAL))


# ---------------------------------------------------------------------------
# Login scoring tests
# ---------------------------------------------------------------------------

class LoginScoringTest(TestCase):

    def setUp(self):
        self.user = _user("+966500050020")
        # Register a known device
        UserDevice.objects.create(
            user=self.user,
            device_uuid="known-device-123",
            device_hash="hash123",
        )

    def test_clean_login_no_alert(self):
        """Single success login, known device → LOW → no alert."""
        log = _login_log(self.user, self.user.phone_number, device_id="known-device-123")
        alert = score_login(log.pk)
        self.assertIsNone(alert)

    def test_new_device_scores(self):
        """Unknown device → +25 → MEDIUM alert."""
        log = _login_log(self.user, self.user.phone_number, device_id="new-device-XYZ")
        alert = score_login(log.pk)
        self.assertIsNotNone(alert)
        self.assertIn(alert.severity, (AlertSeverity.MEDIUM, AlertSeverity.HIGH, AlertSeverity.CRITICAL))

    def test_multiple_failures_score_high(self):
        """3 failed logins + new device → 25+30 = 55 → HIGH."""
        for _ in range(3):
            _login_log(self.user, self.user.phone_number, status=LoginStatus.FAILED, device_id="nd")
        log = _login_log(self.user, self.user.phone_number, device_id="nd")
        alert = score_login(log.pk)
        self.assertIsNotNone(alert)
        self.assertIn(alert.severity, (AlertSeverity.HIGH, AlertSeverity.CRITICAL))

    def test_new_device_failures_new_country_critical(self):
        """New device + 3 failures + new country → 25+30+20 = 75 → CRITICAL."""
        for _ in range(3):
            _login_log(
                self.user, self.user.phone_number,
                status=LoginStatus.FAILED, device_id="intl-device", country="US",
            )
        log = _login_log(
            self.user, self.user.phone_number,
            device_id="intl-device", country="US",
        )
        alert = score_login(log.pk)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)
        self.assertEqual(alert.alert_type, AlertType.LOGIN)

    def test_login_score_written_to_log(self):
        """score_login must update LoginLog.risk_score."""
        log = _login_log(self.user, self.user.phone_number, device_id="new-dev")
        score_login(log.pk)
        log.refresh_from_db()
        self.assertIsNotNone(log.risk_score)

    def test_score_login_missing_log_does_not_raise(self):
        """Calling with non-existent pk must not raise (swallows gracefully)."""
        result = score_login(99999)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------

class SeverityClassificationTest(TestCase):
    def test_severity_boundaries(self):
        self.assertEqual(AlertSeverity.for_score(0),  AlertSeverity.LOW)
        self.assertEqual(AlertSeverity.for_score(24), AlertSeverity.LOW)
        self.assertEqual(AlertSeverity.for_score(25), AlertSeverity.MEDIUM)
        self.assertEqual(AlertSeverity.for_score(49), AlertSeverity.MEDIUM)
        self.assertEqual(AlertSeverity.for_score(50), AlertSeverity.HIGH)
        self.assertEqual(AlertSeverity.for_score(74), AlertSeverity.HIGH)
        self.assertEqual(AlertSeverity.for_score(75), AlertSeverity.CRITICAL)
        self.assertEqual(AlertSeverity.for_score(99), AlertSeverity.CRITICAL)


# ---------------------------------------------------------------------------
# Review / Decision flow
# ---------------------------------------------------------------------------

class ReviewAlertTest(TestCase):

    def setUp(self):
        self.officer = _user("+966500050099")
        self.user    = _user("+966500050030")
        self.account = _account(self.user)
        # Manually create a MEDIUM alert for review tests
        self.alert = FraudAlert.objects.create(
            alert_type=AlertType.TRANSACTION,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.OPEN,
            risk_score=55,
            user=self.user,
            account=self.account,
            rules_triggered=["High-value transaction: 5000"],
        )

    def test_dismiss_sets_dismissed(self):
        decision = review_alert(
            alert_id=self.alert.pk, officer=self.officer, action=DecisionAction.DISMISS
        )
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, AlertStatus.DISMISSED)
        self.assertEqual(decision.action, DecisionAction.DISMISS)

    def test_freeze_account_action(self):
        review_alert(
            alert_id=self.alert.pk,
            officer=self.officer,
            action=DecisionAction.FREEZE_ACCOUNT,
            notes="Confirmed suspicious.",
        )
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, AlertStatus.ACTIONED)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.FROZEN)

    def test_block_account_action(self):
        review_alert(
            alert_id=self.alert.pk,
            officer=self.officer,
            action=DecisionAction.BLOCK_ACCOUNT,
            notes="Fraud confirmed.",
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.BLOCKED)

    def test_warn_action_does_not_touch_account(self):
        review_alert(
            alert_id=self.alert.pk, officer=self.officer, action=DecisionAction.WARN
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.ACTIVE)

    def test_double_review_raises(self):
        review_alert(
            alert_id=self.alert.pk, officer=self.officer, action=DecisionAction.DISMISS
        )
        with self.assertRaises(AlertAlreadyReviewedError):
            review_alert(
                alert_id=self.alert.pk, officer=self.officer, action=DecisionAction.WARN
            )

    def test_dismiss_alert_shortcut(self):
        decision = dismiss_alert(alert_id=self.alert.pk, officer=self.officer)
        self.assertEqual(decision.action, DecisionAction.DISMISS)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, AlertStatus.DISMISSED)


# ---------------------------------------------------------------------------
# Auto-freeze: score_transaction integration test (TransactionTestCase for on_commit)
# ---------------------------------------------------------------------------

class AutoFreezeOnCommitTest(TransactionTestCase):
    """
    Uses TransactionTestCase so that on_commit fires (score_transaction runs),
    and the resulting auto-freeze can be verified.
    """

    def setUp(self):
        from apps.ledger.services import post_transaction
        self._post = post_transaction
        self.user     = _user("+966500050040", kyc=KycStatus.APPROVED)
        self.receiver = _user("+966500050041", kyc=KycStatus.APPROVED)
        _currency()
        self.src = _account(self.user, Decimal("50000.00"))
        self.dst = _account(self.receiver, Decimal("0.00"))

    def test_critical_transaction_auto_freezes_via_on_commit(self):
        """USD 10,000 transfer → on_commit fires score_transaction → CRITICAL → account frozen."""
        tx = self._post(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("10000.00"),
            source_account=self.src,
            destination_account=self.dst,
            customer=self.user,
        )
        # on_commit fires immediately in TransactionTestCase
        self.src.refresh_from_db()
        alert = FraudAlert.objects.filter(transaction=tx, severity=AlertSeverity.CRITICAL).first()
        self.assertIsNotNone(alert, "CRITICAL alert must be created for USD 10,000 transfer")
        self.assertEqual(alert.auto_action_taken, "ACCOUNT_FROZEN")
        self.assertEqual(self.src.status, AccountStatus.FROZEN)
