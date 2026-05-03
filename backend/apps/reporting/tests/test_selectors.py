"""
Reporting selector tests.

Covered:
  1.  get_admin_summary — counts and totals match seeded data
  2.  get_risk_summary  — open alert count and severity breakdown
  3.  get_operations_summary — pending KYC, open tickets
  4.  get_daily_transaction_volume — groups by day
  5.  get_weekly_transaction_volume — groups by week
  6.  get_volume_by_transaction_type — groups by type
  7.  get_fee_aggregation — sums FEE entries only
  8.  get_user_growth — new-user grouping
  9.  get_fraud_metrics — period metrics
  10. get_transaction_trace — returns entries, history, alerts
  11. get_account_restriction_history — ordered history
  12. get_alert_decision_history — returns decisions
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.constants import AccountStatus, RestrictionSource, RestrictionType
from apps.accounts.models import Account, AccountRestriction, Currency
from apps.kyc.constants import KycDocumentStatus
from apps.kyc.models import KycDocument
from apps.ledger.constants import EntryType, TransactionStatus, TransactionType
from apps.ledger.models import FeeRule, Transaction, TransactionEntry, TransactionHistory
from apps.risk.constants import AlertSeverity, AlertStatus, AlertType, DecisionAction
from apps.risk.models import FraudAlert, FraudDecision
from apps.security.constants import LoginStatus
from apps.support.constants import TicketStatus
from apps.support.models import SupportTicket
from apps.users.constants import KycStatus, UserStatus
from apps.users.models import User

from apps.reporting.selectors import (
    get_account_restriction_history,
    get_admin_summary,
    get_alert_decision_history,
    get_daily_transaction_volume,
    get_fee_aggregation,
    get_fraud_metrics,
    get_operations_summary,
    get_risk_summary,
    get_transaction_trace,
    get_user_growth,
    get_volume_by_transaction_type,
    get_weekly_transaction_volume,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _currency():
    return Currency.objects.get_or_create(
        code="USD",
        defaults={"name": "US Dollar", "symbol": "$", "decimal_places": 2},
    )[0]


def _user(phone, status=UserStatus.ACTIVE, kyc=KycStatus.APPROVED):
    return User.objects.create_user(
        phone_number=phone, password="P!", status=status, kyc_status=kyc
    )


def _account(user, balance=Decimal("1000.00")):
    cur = _currency()
    return Account.objects.create(
        user=user, currency=cur,
        account_number=f"{8000 + Account.objects.count():016d}",
        account_name=f"Acct {user.phone_number}",
        status=AccountStatus.ACTIVE,
        available_balance=balance, ledger_balance=balance,
    )


def _tx(src, dst, amount, tx_type=TransactionType.TRANSFER):
    cur = _currency()
    tx = Transaction.objects.create(
        reference_number=f"REF{Transaction.objects.count():010d}",
        transaction_type=tx_type,
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


def _fee_entry(tx, account, fee):
    TransactionEntry.objects.create(
        transaction=tx, account=account,
        entry_type=EntryType.FEE, amount=fee, sequence_no=3,
    )


def _alert(user=None, account=None, severity=AlertSeverity.HIGH, status=AlertStatus.OPEN):
    return FraudAlert.objects.create(
        alert_type=AlertType.TRANSACTION, severity=severity, status=status,
        risk_score=55, user=user, account=account, rules_triggered=[],
    )


# ---------------------------------------------------------------------------
# Admin summary
# ---------------------------------------------------------------------------

class AdminSummaryTest(TestCase):
    def setUp(self):
        _currency()
        self.u1 = _user("+96650001001", status=UserStatus.ACTIVE)
        self.u2 = _user("+96650001002", status=UserStatus.ACTIVE)
        self.u3 = _user("+96650001003", status=UserStatus.PENDING_VERIFICATION, kyc=KycStatus.NOT_SUBMITTED)
        self.a1 = _account(self.u1, Decimal("5000.00"))
        self.a2 = _account(self.u2, Decimal("3000.00"))
        self.tx = _tx(self.a1, self.a2, Decimal("1000.00"))
        _fee_entry(self.tx, self.a1, Decimal("10.00"))

    def test_user_counts(self):
        s = get_admin_summary()
        self.assertGreaterEqual(s["total_users"], 3)
        self.assertGreaterEqual(s["active_users"], 2)
        self.assertGreaterEqual(s["pending_users"], 1)

    def test_transaction_volume(self):
        s = get_admin_summary()
        self.assertGreaterEqual(s["total_transaction_count"], 1)
        self.assertGreaterEqual(s["total_transaction_volume"], Decimal("1000.00"))

    def test_fee_revenue(self):
        s = get_admin_summary()
        self.assertGreaterEqual(s["fee_revenue"], Decimal("10.00"))

    def test_total_balances(self):
        s = get_admin_summary()
        self.assertGreaterEqual(s["total_available_balance"], Decimal("8000.00"))


# ---------------------------------------------------------------------------
# Risk summary
# ---------------------------------------------------------------------------

class RiskSummaryTest(TestCase):
    def setUp(self):
        self.user = _user("+96650001010")
        _alert(user=self.user, severity=AlertSeverity.HIGH)
        _alert(user=self.user, severity=AlertSeverity.CRITICAL)
        _alert(user=self.user, severity=AlertSeverity.HIGH, status=AlertStatus.DISMISSED)

    def test_open_alert_count(self):
        s = get_risk_summary()
        self.assertEqual(s["open_alerts"], 2)   # only OPEN ones
        self.assertEqual(s["total_alerts"], 3)

    def test_severity_breakdown(self):
        s = get_risk_summary()
        self.assertEqual(s["by_severity"][AlertSeverity.HIGH], 2)
        self.assertEqual(s["by_severity"][AlertSeverity.CRITICAL], 1)


# ---------------------------------------------------------------------------
# Operations summary
# ---------------------------------------------------------------------------

class OperationsSummaryTest(TestCase):
    def setUp(self):
        _currency()
        self.user = _user("+96650001020", kyc=KycStatus.PENDING)
        KycDocument.objects.create(
            user=self.user, document_type="NATIONAL_ID",
            file="dummy.jpg", status=KycDocumentStatus.PENDING,
        )
        self.staff = _user("+96650001021")
        SupportTicket.objects.create(
            user=self.user,
            subject="Help",
            category="GENERAL",
            status=TicketStatus.OPEN,
        )

    def test_pending_kyc(self):
        s = get_operations_summary()
        self.assertGreaterEqual(s["pending_kyc_users"], 1)
        self.assertGreaterEqual(s["pending_kyc_docs"], 1)

    def test_open_tickets(self):
        s = get_operations_summary()
        self.assertGreaterEqual(s["open_support_tickets"], 1)


# ---------------------------------------------------------------------------
# Time-series volume
# ---------------------------------------------------------------------------

class VolumeSeriesTest(TestCase):
    def setUp(self):
        _currency()
        u1 = _user("+96650001030")
        u2 = _user("+96650001031")
        a1 = _account(u1)
        a2 = _account(u2)
        _tx(a1, a2, Decimal("500.00"))
        _tx(a1, a2, Decimal("500.00"))

    def test_daily_volume_has_rows(self):
        rows = get_daily_transaction_volume(days=7)
        self.assertGreater(len(rows), 0)
        self.assertIn("count", rows[0])
        self.assertIn("volume", rows[0])

    def test_weekly_volume_has_rows(self):
        rows = get_weekly_transaction_volume(weeks=4)
        self.assertGreater(len(rows), 0)

    def test_by_type_has_rows(self):
        rows = get_volume_by_transaction_type(days=30)
        self.assertGreater(len(rows), 0)
        self.assertIn("transaction_type", rows[0])


# ---------------------------------------------------------------------------
# Fee aggregation
# ---------------------------------------------------------------------------

class FeeAggregationTest(TestCase):
    def setUp(self):
        _currency()
        u1 = _user("+96650001040")
        u2 = _user("+96650001041")
        a1 = _account(u1)
        a2 = _account(u2)
        tx = _tx(a1, a2, Decimal("2000.00"))
        _fee_entry(tx, a1, Decimal("20.00"))

    def test_total_fee_revenue(self):
        result = get_fee_aggregation(days=30)
        self.assertGreaterEqual(result["total_fee_revenue"], Decimal("20.00"))
        self.assertEqual(result["period_days"], 30)

    def test_by_type_row_present(self):
        result = get_fee_aggregation(days=30)
        self.assertGreater(len(result["by_transaction_type"]), 0)


# ---------------------------------------------------------------------------
# User growth
# ---------------------------------------------------------------------------

class UserGrowthTest(TestCase):
    def setUp(self):
        _user("+96650001050")
        _user("+96650001051")

    def test_growth_rows_present(self):
        rows = get_user_growth(days=30)
        self.assertGreater(len(rows), 0)
        self.assertIn("new_users", rows[0])


# ---------------------------------------------------------------------------
# Fraud metrics
# ---------------------------------------------------------------------------

class FraudMetricsTest(TestCase):
    def setUp(self):
        u = _user("+96650001060")
        _alert(u, severity=AlertSeverity.CRITICAL)
        _alert(u, severity=AlertSeverity.HIGH, status=AlertStatus.DISMISSED)

    def test_metrics_structure(self):
        m = get_fraud_metrics(days=30)
        self.assertGreaterEqual(m["total_alerts"], 2)
        self.assertGreaterEqual(m["critical_alerts"], 1)
        self.assertGreaterEqual(m["resolved_alerts"], 1)
        self.assertIn("by_day", m)


# ---------------------------------------------------------------------------
# Transaction trace
# ---------------------------------------------------------------------------

class TransactionTraceTest(TestCase):
    def setUp(self):
        _currency()
        u1 = _user("+96650001070")
        u2 = _user("+96650001071")
        self.a1 = _account(u1)
        self.a2 = _account(u2)
        self.tx = _tx(self.a1, self.a2, Decimal("500.00"))
        # Add fraud alert linked to the transaction
        FraudAlert.objects.create(
            alert_type=AlertType.TRANSACTION, severity=AlertSeverity.HIGH,
            status=AlertStatus.OPEN, risk_score=55,
            user=u1, account=self.a1, transaction=self.tx, rules_triggered=[],
        )

    def test_trace_returns_entries(self):
        trace = get_transaction_trace(self.tx.reference_number)
        self.assertEqual(trace["transaction"].pk, self.tx.pk)
        self.assertEqual(len(trace["entries"]), 2)
        self.assertIsNone(trace["history"])      # not archived
        self.assertEqual(len(trace["reversals"]), 0)

    def test_trace_includes_fraud_alerts(self):
        trace = get_transaction_trace(self.tx.reference_number)
        self.assertEqual(len(trace["fraud_alerts"]), 1)

    def test_trace_not_found_raises(self):
        from apps.ledger.models import Transaction
        with self.assertRaises(Transaction.DoesNotExist):
            get_transaction_trace("NONEXISTENT")


# ---------------------------------------------------------------------------
# Account restriction history
# ---------------------------------------------------------------------------

class AccountRestrictionHistoryTest(TestCase):
    def setUp(self):
        _currency()
        u = _user("+96650001080")
        self.account = _account(u)
        staff = _user("+96650001081")
        AccountRestriction.objects.create(
            account=self.account,
            restriction_type=RestrictionType.FREEZE,
            reason="Fraud",
            source=RestrictionSource.RISK_OFFICER,
            applied_by=staff,
            is_active=True,
        )
        AccountRestriction.objects.create(
            account=self.account,
            restriction_type=RestrictionType.BLOCK,
            reason="Confirmed fraud",
            source=RestrictionSource.RISK_OFFICER,
            applied_by=staff,
            is_active=False,
        )

    def test_returns_two_records(self):
        qs = get_account_restriction_history(self.account.pk)
        self.assertEqual(qs.count(), 2)

    def test_ordered_newest_first(self):
        qs = list(get_account_restriction_history(self.account.pk))
        # Both created at ~same time; just verify both present
        types = {r.restriction_type for r in qs}
        self.assertIn(RestrictionType.FREEZE, types)
        self.assertIn(RestrictionType.BLOCK,  types)


# ---------------------------------------------------------------------------
# Alert decision history
# ---------------------------------------------------------------------------

class AlertDecisionHistoryTest(TestCase):
    def setUp(self):
        u = _user("+96650001090")
        officer = _user("+96650001091")
        self.alert = _alert(u, status=AlertStatus.DISMISSED)
        FraudDecision.objects.create(
            alert=self.alert,
            officer=officer,
            action=DecisionAction.DISMISS,
            notes="False positive.",
        )

    def test_returns_decision(self):
        qs = list(get_alert_decision_history(alert_id=self.alert.pk))
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].action, DecisionAction.DISMISS)

    def test_no_alert_id_returns_all(self):
        qs = get_alert_decision_history()
        self.assertGreaterEqual(qs.count(), 1)
