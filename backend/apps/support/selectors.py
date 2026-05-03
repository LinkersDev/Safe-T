"""Read-only queries for the support app."""
from .constants import TicketStatus
from .models import Notification, SupportTicket, SupportTicketMessage


def get_user_tickets(user_id: int):
    return (
        SupportTicket.objects
        .filter(user_id=user_id)
        .select_related("assigned_to")
        .order_by("-created_at")
    )


def get_ticket_for_user(ticket_id: int, user_id: int) -> SupportTicket:
    """Return ticket owned by user_id, raise DoesNotExist if not found/owned."""
    return SupportTicket.objects.select_related("assigned_to").get(
        pk=ticket_id, user_id=user_id
    )


def get_ticket_messages(ticket_id: int, *, include_internal: bool = False):
    """Return messages for a ticket. Excludes internal notes unless staff."""
    qs = SupportTicketMessage.objects.filter(ticket_id=ticket_id).select_related("sender")
    if not include_internal:
        qs = qs.filter(is_internal=False)
    return qs


def get_all_tickets(*, status: str | None = None, unassigned_only: bool = False):
    """Staff: return all tickets, optionally filtered by status / unassigned."""
    qs = SupportTicket.objects.select_related("user", "assigned_to").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if unassigned_only:
        qs = qs.filter(assigned_to__isnull=True)
    return qs


def get_ticket_by_id(ticket_id: int) -> SupportTicket:
    return SupportTicket.objects.select_related("user", "assigned_to").get(pk=ticket_id)


def get_user_notifications(user_id: int, *, unread_only: bool = False):
    qs = Notification.objects.filter(user_id=user_id)
    if unread_only:
        qs = qs.filter(is_read=False)
    return qs


def unread_notification_count(user_id: int) -> int:
    return Notification.objects.filter(user_id=user_id, is_read=False).count()
