"""
Support write-path services.

Rules:
  - All ticket state transitions go through service functions.
  - Notifications are always created via `dispatch_notification` — never directly.
  - `dispatch_post_transaction_notifications` is called by post_transaction on_commit;
    it must swallow all exceptions so a notification failure cannot undo a committed tx.
"""
import logging
from decimal import Decimal

from django.utils import timezone

from .constants import NotificationType, TicketCategory, TicketStatus
from .exceptions import TicketClosedError, TicketNotFoundError, UnauthorizedTicketAccessError
from .models import Notification, SupportTicket, SupportTicketMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def dispatch_notification(
    *,
    user,
    notification_type: str,
    title: str,
    message: str,
    reference_type: str = "",
    reference_id: str = "",
) -> Notification:
    """Create an in-app notification for *user*."""
    notif = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    logger.debug(
        "Notification dispatched | user=%s type=%s ref=%s/%s",
        user.pk, notification_type, reference_type, reference_id,
    )
    return notif


def mark_notification_read(*, notification_id: int, user) -> Notification:
    try:
        notif = Notification.objects.get(pk=notification_id, user=user)
    except Notification.DoesNotExist:
        from .exceptions import NotificationNotFoundError
        raise NotificationNotFoundError(f"Notification {notification_id} not found.")
    if not notif.is_read:
        notif.is_read = True
        notif.read_at = timezone.now()
        notif.save(update_fields=["is_read", "read_at"])
    return notif


def mark_all_notifications_read(*, user) -> int:
    """Mark every unread notification for *user* as read. Returns count updated."""
    count = Notification.objects.filter(user=user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    return count


# ---------------------------------------------------------------------------
# Post-transaction notification dispatch (on_commit hook target)
# ---------------------------------------------------------------------------

def dispatch_post_transaction_notifications(tx_pk: int) -> None:
    """
    Called via db_transaction.on_commit() after post_transaction() commits.

    Creates TRANSACTION_SENT for the customer (debited side) and
    TRANSACTION_RECEIVED for the destination account owner.

    Swallows ALL exceptions — a notification failure must never surface
    to the caller after the financial transaction has already committed.
    """
    try:
        from apps.ledger.models import Transaction, TransactionEntry
        from apps.ledger.constants import EntryType, TransactionType

        tx = (
            Transaction.objects
            .select_related("customer", "currency")
            .get(pk=tx_pk)
        )

        amount   = tx.amount
        currency = tx.currency.code if tx.currency else "USD"
        ref      = tx.reference_number
        tx_type  = tx.transaction_type

        # Derive users from entries: seq=1 is always DEBIT (sender), seq=2 is CREDIT (receiver)
        entries = (
            TransactionEntry.objects
            .filter(transaction=tx)
            .select_related("account__user")
            .order_by("sequence_no")
        )

        sender_user   = tx.customer
        receiver_user = None
        for entry in entries:
            if entry.entry_type == EntryType.CREDIT and entry.sequence_no == 2:
                receiver_user = entry.account.user
                break

        # Sender notification
        if sender_user:
            if tx_type == TransactionType.TRANSFER:
                title   = "Transfer Sent"
                message = (
                    f"Your transfer of {currency} {amount} has been completed. "
                    f"Reference: {ref}."
                )
            elif tx_type == TransactionType.QR_PAYMENT:
                title   = "QR Payment Sent"
                message = f"QR payment of {currency} {amount} processed. Reference: {ref}."
            elif tx_type == TransactionType.BILL_PAYMENT:
                title   = "Bill Payment Sent"
                message = f"Bill payment of {currency} {amount} completed. Reference: {ref}."
            else:
                title   = "Transaction Completed"
                message = f"{currency} {amount} transaction completed. Reference: {ref}."

            dispatch_notification(
                user=sender_user,
                notification_type=NotificationType.TRANSACTION_SENT,
                title=title,
                message=message,
                reference_type="transaction",
                reference_id=ref,
            )

        # Receiver notification
        if receiver_user and receiver_user != sender_user:
            if tx_type == TransactionType.TRANSFER:
                title   = "Transfer Received"
                message = (
                    f"You received {currency} {amount}. "
                    f"Reference: {ref}."
                )
            elif tx_type == TransactionType.QR_PAYMENT:
                title   = "QR Payment Received"
                message = f"QR payment of {currency} {amount} received. Reference: {ref}."
            elif tx_type == TransactionType.BILL_PAYMENT:
                title   = "Bill Payment Received"
                message = f"Bill payment of {currency} {amount} received. Reference: {ref}."
            else:
                title   = "Payment Received"
                message = f"{currency} {amount} received. Reference: {ref}."

            dispatch_notification(
                user=receiver_user,
                notification_type=NotificationType.TRANSACTION_RECEIVED,
                title=title,
                message=message,
                reference_type="transaction",
                reference_id=ref,
            )

    except Exception as exc:
        logger.error(
            "dispatch_post_transaction_notifications failed | tx_pk=%s error=%s",
            tx_pk, exc, exc_info=True,
        )


# ---------------------------------------------------------------------------
# Support Tickets
# ---------------------------------------------------------------------------

def create_ticket(
    *,
    user,
    subject: str,
    body: str,
    category: str = TicketCategory.GENERAL,
) -> SupportTicket:
    """Create a new support ticket with the opening message."""
    ticket = SupportTicket.objects.create(
        user=user,
        subject=subject,
        category=category,
        status=TicketStatus.OPEN,
    )
    SupportTicketMessage.objects.create(
        ticket=ticket,
        sender=user,
        body=body,
        is_internal=False,
    )
    logger.info("Support ticket created | ticket=%s user=%s", ticket.pk, user.pk)
    return ticket


def reply_to_ticket(
    *,
    ticket_id: int,
    sender,
    body: str,
    is_internal: bool = False,
    customer_user=None,
) -> SupportTicketMessage:
    """
    Add a reply to a ticket.

    - `customer_user` is set when the reply is from the ticket owner;
      they cannot reply to RESOLVED/CLOSED tickets.
    - Staff can reply to any ticket in any status, and can set is_internal=True.
    """
    try:
        ticket = SupportTicket.objects.get(pk=ticket_id)
    except SupportTicket.DoesNotExist:
        raise TicketNotFoundError(f"Ticket {ticket_id} not found.")

    # Customer can only reply to active tickets
    if customer_user is not None:
        if ticket.user_id != customer_user.pk:
            raise UnauthorizedTicketAccessError("You do not own this ticket.")
        if ticket.status not in TicketStatus.ACTIVE_STATUSES:
            raise TicketClosedError(
                f"Ticket #{ticket_id} is {ticket.status} and cannot receive new messages."
            )

    msg = SupportTicketMessage.objects.create(
        ticket=ticket,
        sender=sender,
        body=body,
        is_internal=is_internal,
    )

    # Auto-reopen if customer replies to an in-progress ticket (optional UX)
    if customer_user and ticket.status == TicketStatus.IN_PROGRESS:
        pass  # stays IN_PROGRESS until staff resolves

    logger.info("Ticket reply added | ticket=%s sender=%s internal=%s", ticket_id, sender.pk, is_internal)
    return msg


def assign_ticket(*, ticket_id: int, staff_user) -> SupportTicket:
    """Assign a ticket to *staff_user* and set status to IN_PROGRESS."""
    try:
        ticket = SupportTicket.objects.get(pk=ticket_id)
    except SupportTicket.DoesNotExist:
        raise TicketNotFoundError(f"Ticket {ticket_id} not found.")

    ticket.assigned_to = staff_user
    ticket.status      = TicketStatus.IN_PROGRESS
    ticket.save(update_fields=["assigned_to", "status", "updated_at"])
    logger.info("Ticket assigned | ticket=%s staff=%s", ticket_id, staff_user.pk)
    return ticket


def resolve_ticket(*, ticket_id: int, staff_user) -> SupportTicket:
    """Mark a ticket as RESOLVED."""
    try:
        ticket = SupportTicket.objects.get(pk=ticket_id)
    except SupportTicket.DoesNotExist:
        raise TicketNotFoundError(f"Ticket {ticket_id} not found.")

    ticket.status      = TicketStatus.RESOLVED
    ticket.resolved_at = timezone.now()
    ticket.save(update_fields=["status", "resolved_at", "updated_at"])

    # Notify the customer
    dispatch_notification(
        user=ticket.user,
        notification_type=NotificationType.TICKET_RESOLVED,
        title="Support Ticket Resolved",
        message=f'Your support ticket "{ticket.subject}" has been resolved.',
        reference_type="ticket",
        reference_id=str(ticket.pk),
    )

    logger.info("Ticket resolved | ticket=%s staff=%s", ticket_id, staff_user.pk)
    return ticket


def close_ticket(*, ticket_id: int, closed_by) -> SupportTicket:
    """Mark a ticket as CLOSED (can be done by customer or staff)."""
    try:
        ticket = SupportTicket.objects.get(pk=ticket_id)
    except SupportTicket.DoesNotExist:
        raise TicketNotFoundError(f"Ticket {ticket_id} not found.")

    ticket.status   = TicketStatus.CLOSED
    ticket.closed_at = timezone.now()
    ticket.save(update_fields=["status", "closed_at", "updated_at"])
    logger.info("Ticket closed | ticket=%s by=%s", ticket_id, closed_by.pk)
    return ticket
