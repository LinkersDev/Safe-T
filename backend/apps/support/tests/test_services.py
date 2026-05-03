"""
Unit tests for support services and notification dispatch.

Covered:
  1.  create_ticket: creates ticket + opening message
  2.  reply_to_ticket: customer reply, staff reply, internal note
  3.  assign_ticket: sets status IN_PROGRESS and assigned_to
  4.  resolve_ticket: sets status RESOLVED, creates notification for customer
  5.  close_ticket: sets status CLOSED
  6.  Closed ticket rejects customer reply
  7.  Non-owner cannot reply
  8.  mark_notification_read / mark_all_notifications_read
  9.  dispatch_notification: creates Notification record
  10. dispatch_post_transaction_notifications: creates SENT + RECEIVED after transfer
  11. Notification dispatch failure does NOT bubble up
"""
from decimal import Decimal

from django.test import TestCase, TransactionTestCase

from apps.accounts.constants import AccountStatus
from apps.accounts.models import Account, Currency
from apps.ledger.constants import TransactionType
from apps.ledger.services import post_transaction
from apps.users.constants import KycStatus, UserStatus
from apps.users.models import User

from apps.support.constants import NotificationType, TicketCategory, TicketStatus
from apps.support.exceptions import TicketClosedError, UnauthorizedTicketAccessError
from apps.support.models import Notification, SupportTicket, SupportTicketMessage
from apps.support.services import (
    assign_ticket,
    close_ticket,
    create_ticket,
    dispatch_notification,
    dispatch_post_transaction_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    reply_to_ticket,
    resolve_ticket,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(phone, status=UserStatus.ACTIVE, kyc=KycStatus.APPROVED):
    return User.objects.create_user(
        phone_number=phone, password="Pass1!", status=status, kyc_status=kyc
    )


def _currency():
    return Currency.objects.get_or_create(
        code="USD", defaults={"name": "US Dollar", "symbol": "$", "decimal_places": 2}
    )[0]


def _account(user, balance=Decimal("500.00")):
    return Account.objects.create(
        user=user, currency=_currency(),
        account_number=f"{5000 + Account.objects.count():016d}",
        account_name=f"Acct {user.phone_number}",
        status=AccountStatus.ACTIVE,
        available_balance=balance, ledger_balance=balance,
    )


# ---------------------------------------------------------------------------
# Support ticket service tests
# ---------------------------------------------------------------------------

class CreateTicketTest(TestCase):
    def setUp(self):
        self.customer = _user("+966500030001")
        self.staff    = _user("+966500030099")

    def test_create_ticket_returns_ticket(self):
        ticket = create_ticket(
            user=self.customer, subject="Cannot login", body="I keep getting OTP errors."
        )
        self.assertIsInstance(ticket, SupportTicket)
        self.assertEqual(ticket.status, TicketStatus.OPEN)
        self.assertEqual(ticket.user, self.customer)

    def test_opening_message_is_created(self):
        ticket = create_ticket(
            user=self.customer, subject="Test", body="Opening message body"
        )
        msgs = SupportTicketMessage.objects.filter(ticket=ticket)
        self.assertEqual(msgs.count(), 1)
        self.assertEqual(msgs.first().body, "Opening message body")
        self.assertFalse(msgs.first().is_internal)

    def test_category_saved(self):
        ticket = create_ticket(
            user=self.customer, subject="Payment", body="Bill not paid",
            category=TicketCategory.PAYMENT_ISSUE,
        )
        self.assertEqual(ticket.category, TicketCategory.PAYMENT_ISSUE)


class ReplyToTicketTest(TestCase):
    def setUp(self):
        self.customer = _user("+966500030002")
        self.staff    = _user("+966500030098")
        self.ticket   = create_ticket(user=self.customer, subject="S", body="Body")

    def test_customer_reply(self):
        msg = reply_to_ticket(
            ticket_id=self.ticket.pk, sender=self.customer, body="Follow up",
            customer_user=self.customer,
        )
        self.assertEqual(msg.body, "Follow up")
        self.assertFalse(msg.is_internal)

    def test_staff_reply_public(self):
        msg = reply_to_ticket(
            ticket_id=self.ticket.pk, sender=self.staff, body="Staff answer"
        )
        self.assertFalse(msg.is_internal)

    def test_staff_internal_note(self):
        msg = reply_to_ticket(
            ticket_id=self.ticket.pk, sender=self.staff,
            body="Internal note here", is_internal=True,
        )
        self.assertTrue(msg.is_internal)

    def test_non_owner_cannot_reply(self):
        other = _user("+966500030003")
        with self.assertRaises(UnauthorizedTicketAccessError):
            reply_to_ticket(
                ticket_id=self.ticket.pk, sender=other, body="Hack",
                customer_user=other,
            )

    def test_closed_ticket_rejects_customer_reply(self):
        close_ticket(ticket_id=self.ticket.pk, closed_by=self.customer)
        with self.assertRaises(TicketClosedError):
            reply_to_ticket(
                ticket_id=self.ticket.pk, sender=self.customer, body="Reopen?",
                customer_user=self.customer,
            )


class AssignResolveCloseTest(TestCase):
    def setUp(self):
        self.customer = _user("+966500030004")
        self.staff    = _user("+966500030097")
        self.ticket   = create_ticket(user=self.customer, subject="X", body="Y")

    def test_assign_sets_in_progress(self):
        t = assign_ticket(ticket_id=self.ticket.pk, staff_user=self.staff)
        self.assertEqual(t.status, TicketStatus.IN_PROGRESS)
        self.assertEqual(t.assigned_to, self.staff)

    def test_resolve_sets_resolved_and_notifies(self):
        t = resolve_ticket(ticket_id=self.ticket.pk, staff_user=self.staff)
        self.assertEqual(t.status, TicketStatus.RESOLVED)
        self.assertIsNotNone(t.resolved_at)
        # Customer should have a TICKET_RESOLVED notification
        notif = Notification.objects.filter(
            user=self.customer,
            notification_type=NotificationType.TICKET_RESOLVED,
        ).first()
        self.assertIsNotNone(notif)

    def test_close_sets_closed(self):
        t = close_ticket(ticket_id=self.ticket.pk, closed_by=self.staff)
        self.assertEqual(t.status, TicketStatus.CLOSED)
        self.assertIsNotNone(t.closed_at)


# ---------------------------------------------------------------------------
# Notification service tests
# ---------------------------------------------------------------------------

class DispatchNotificationTest(TestCase):
    def setUp(self):
        self.user = _user("+966500030005")

    def test_dispatch_creates_notification(self):
        notif = dispatch_notification(
            user=self.user,
            notification_type=NotificationType.SYSTEM,
            title="Hello",
            message="World",
        )
        self.assertIsInstance(notif, Notification)
        self.assertFalse(notif.is_read)

    def test_mark_read(self):
        notif = dispatch_notification(
            user=self.user, notification_type=NotificationType.SYSTEM,
            title="T", message="M",
        )
        updated = mark_notification_read(notification_id=notif.pk, user=self.user)
        self.assertTrue(updated.is_read)
        self.assertIsNotNone(updated.read_at)

    def test_mark_all_read(self):
        for i in range(3):
            dispatch_notification(
                user=self.user, notification_type=NotificationType.SYSTEM,
                title=f"N{i}", message="m",
            )
        count = mark_all_notifications_read(user=self.user)
        self.assertEqual(count, 3)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)


# ---------------------------------------------------------------------------
# Post-transaction notification dispatch (uses TransactionTestCase for on_commit)
# ---------------------------------------------------------------------------

class PostTransactionNotificationTest(TransactionTestCase):
    """
    TransactionTestCase is required because on_commit() only fires after a
    real commit — TestCase wraps everything in a savepoint and on_commit
    callbacks never run.
    """

    def setUp(self):
        self.sender   = _user("+966500030010", kyc=KycStatus.APPROVED)
        self.receiver = _user("+966500030011", kyc=KycStatus.APPROVED)
        _currency()
        self.src = _account(self.sender, Decimal("500.00"))
        self.dst = _account(self.receiver, Decimal("0.00"))

    def test_notifications_created_after_transfer(self):
        tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            currency_code="USD",
            amount=Decimal("100.00"),
            source_account=self.src,
            destination_account=self.dst,
            customer=self.sender,
        )
        # on_commit fires immediately in TransactionTestCase
        sent_notifs = Notification.objects.filter(
            user=self.sender,
            notification_type=NotificationType.TRANSACTION_SENT,
            reference_id=tx.reference_number,
        )
        recv_notifs = Notification.objects.filter(
            user=self.receiver,
            notification_type=NotificationType.TRANSACTION_RECEIVED,
            reference_id=tx.reference_number,
        )
        self.assertEqual(sent_notifs.count(), 1)
        self.assertEqual(recv_notifs.count(), 1)
        self.assertIn(str(tx.amount), sent_notifs.first().message)

    def test_dispatch_dispatch_failure_does_not_raise(self):
        """Even if notification dispatch fails internally, the tx is fine."""
        # This tests that the _notify wrapper swallows exceptions.
        # We can simulate this by calling dispatch_post_transaction_notifications
        # with a non-existent tx_pk.
        try:
            dispatch_post_transaction_notifications(99999)
        except Exception:
            self.fail("dispatch_post_transaction_notifications should not raise.")
        # No notification created
        self.assertEqual(Notification.objects.count(), 0)
