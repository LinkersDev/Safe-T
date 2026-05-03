"""
Support API views.

Customer endpoints (prefix: /api/support/)
  GET  /api/support/tickets/                → list own tickets
  POST /api/support/tickets/                → create ticket
  GET  /api/support/tickets/{id}/           → ticket detail + messages
  POST /api/support/tickets/{id}/reply/     → customer reply
  POST /api/support/tickets/{id}/close/     → customer closes ticket
  GET  /api/support/notifications/          → list notifications
  GET  /api/support/notifications/unread-count/  → unread count
  POST /api/support/notifications/read-all/ → mark all as read
  POST /api/support/notifications/{id}/read/ → mark one as read

Staff endpoints (prefix: /api/staff/support/)
  GET  /api/staff/support/tickets/                 → all tickets (filter by status)
  GET  /api/staff/support/tickets/{id}/            → ticket detail (with internals)
  POST /api/staff/support/tickets/{id}/reply/      → staff reply (supports is_internal)
  POST /api/staff/support/tickets/{id}/assign/     → assign to self
  POST /api/staff/support/tickets/{id}/resolve/    → mark resolved
  POST /api/staff/support/tickets/{id}/close/      → mark closed
"""
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import HasPermission

from .exceptions import (
    TicketClosedError,
    TicketNotFoundError,
    UnauthorizedTicketAccessError,
)
from .selectors import (
    get_all_tickets,
    get_ticket_by_id,
    get_ticket_for_user,
    get_ticket_messages,
    get_user_notifications,
    get_user_tickets,
    unread_notification_count,
)
from .serializers import (
    CreateTicketSerializer,
    NotificationSerializer,
    ReplyTicketSerializer,
    StaffAssignTicketSerializer,
    StaffReplyTicketSerializer,
    StaffResolveTicketSerializer,
    SupportTicketDetailSerializer,
    SupportTicketSerializer,
)
from .services import (
    assign_ticket,
    close_ticket,
    create_ticket,
    mark_all_notifications_read,
    mark_notification_read,
    reply_to_ticket,
    resolve_ticket,
)

logger = logging.getLogger(__name__)


def _require_support_perm(request):
    if not HasPermission.user_has_perm(request.user, "manage_support_tickets"):
        return Response(
            {"detail": "You do not have permission to manage support tickets."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


# ---------------------------------------------------------------------------
# Customer — Tickets
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def ticket_list_create(request):
    if request.method == "GET":
        tickets = get_user_tickets(request.user.pk)
        return Response(SupportTicketSerializer(tickets, many=True).data)

    ser = CreateTicketSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    ticket = create_ticket(
        user=request.user,
        subject=ser.validated_data["subject"],
        body=ser.validated_data["body"],
        category=ser.validated_data["category"],
    )
    return Response(SupportTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ticket_detail(request, ticket_id: int):
    try:
        ticket = get_ticket_for_user(ticket_id, request.user.pk)
    except SupportTicket.DoesNotExist:
        return Response({"detail": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)

    messages = get_ticket_messages(ticket_id, include_internal=False)
    data = SupportTicketDetailSerializer(ticket).data
    from .serializers import SupportTicketMessageSerializer
    data["messages"] = SupportTicketMessageSerializer(messages, many=True).data
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ticket_reply(request, ticket_id: int):
    ser = ReplyTicketSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        msg = reply_to_ticket(
            ticket_id=ticket_id,
            sender=request.user,
            body=ser.validated_data["body"],
            customer_user=request.user,
        )
    except TicketNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except (TicketClosedError, UnauthorizedTicketAccessError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    from .serializers import SupportTicketMessageSerializer
    return Response(SupportTicketMessageSerializer(msg).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ticket_close(request, ticket_id: int):
    try:
        ticket = get_ticket_for_user(ticket_id, request.user.pk)
        closed = close_ticket(ticket_id=ticket.pk, closed_by=request.user)
    except SupportTicket.DoesNotExist:
        return Response({"detail": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)
    except TicketNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    return Response({"detail": "Ticket closed.", "status": closed.status})


# ---------------------------------------------------------------------------
# Customer — Notifications
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    unread_only = request.query_params.get("unread") == "1"
    notifs = get_user_notifications(request.user.pk, unread_only=unread_only)
    return Response(NotificationSerializer(notifs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_unread_count(request):
    return Response({"unread_count": unread_notification_count(request.user.pk)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_read_all(request):
    count = mark_all_notifications_read(user=request.user)
    return Response({"marked_read": count})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_read_one(request, notification_id: int):
    try:
        notif = mark_notification_read(notification_id=notification_id, user=request.user)
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    return Response(NotificationSerializer(notif).data)


# ---------------------------------------------------------------------------
# Staff — Tickets
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_ticket_list(request):
    err = _require_support_perm(request)
    if err:
        return err
    filter_status = request.query_params.get("status")
    unassigned = (request.query_params.get("unassigned") or "").strip().lower() in {"1", "true", "yes"}
    tickets = get_all_tickets(status=filter_status, unassigned_only=unassigned)
    return Response(SupportTicketSerializer(tickets, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_ticket_detail(request, ticket_id: int):
    err = _require_support_perm(request)
    if err:
        return err
    try:
        ticket = get_ticket_by_id(ticket_id)
    except SupportTicket.DoesNotExist:
        return Response({"detail": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)
    messages = get_ticket_messages(ticket_id, include_internal=True)
    data = SupportTicketDetailSerializer(ticket).data
    from .serializers import SupportTicketMessageSerializer
    data["messages"] = SupportTicketMessageSerializer(messages, many=True).data
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def staff_ticket_reply(request, ticket_id: int):
    err = _require_support_perm(request)
    if err:
        return err
    ser = StaffReplyTicketSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        msg = reply_to_ticket(
            ticket_id=ticket_id,
            sender=request.user,
            body=ser.validated_data["body"],
            is_internal=ser.validated_data["is_internal"],
        )
    except TicketNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    from .serializers import SupportTicketMessageSerializer
    return Response(SupportTicketMessageSerializer(msg).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def staff_ticket_assign(request, ticket_id: int):
    err = _require_support_perm(request)
    if err:
        return err
    ser = StaffAssignTicketSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        ticket = assign_ticket(ticket_id=ticket_id, staff_user=request.user)
    except TicketNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    return Response({"detail": "Ticket assigned.", "status": ticket.status, "assigned_to": request.user.full_name})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def staff_ticket_resolve(request, ticket_id: int):
    err = _require_support_perm(request)
    if err:
        return err
    ser = StaffResolveTicketSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        ticket = resolve_ticket(ticket_id=ticket_id, staff_user=request.user)
    except TicketNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    return Response({"detail": "Ticket resolved.", "status": ticket.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def staff_ticket_close(request, ticket_id: int):
    err = _require_support_perm(request)
    if err:
        return err
    try:
        ticket = close_ticket(ticket_id=ticket_id, closed_by=request.user)
    except TicketNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    return Response({"detail": "Ticket closed.", "status": ticket.status})


# Import needed for isinstance check inside views
from .models import SupportTicket  # noqa: E402
