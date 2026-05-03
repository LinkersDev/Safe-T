"""
Integration tests for support API endpoints.

Covered:
  1.  GET  /api/support/tickets/            → lists own tickets
  2.  POST /api/support/tickets/            → creates ticket
  3.  GET  /api/support/tickets/{id}/       → detail (no internal notes)
  4.  POST /api/support/tickets/{id}/reply/ → customer reply
  5.  POST /api/support/tickets/{id}/close/ → customer closes
  6.  GET  /api/support/notifications/      → list + unread filter
  7.  POST /api/support/notifications/read-all/ → mark all read
  8.  POST /api/support/notifications/{id}/read/ → mark one read
  9.  Staff list / detail / reply (internal note hidden from customer) / assign / resolve / close
  10. Staff permission enforcement
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.constants import KycStatus, UserStatus
from apps.users.models import Permission, Role, RolePermission, User

from apps.support.constants import NotificationType, TicketCategory, TicketStatus
from apps.support.models import Notification, SupportTicket
from apps.support.services import create_ticket, dispatch_notification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(phone, status=UserStatus.ACTIVE, kyc=KycStatus.APPROVED):
    return User.objects.create_user(
        phone_number=phone, password="Pass1!", status=status, kyc_status=kyc
    )


def _staff_with_support_perm(phone="+966599902001"):
    role, _ = Role.objects.get_or_create(code="CUSTOMER_SERVICE", defaults={"name": "CS"})
    perm, _ = Permission.objects.get_or_create(
        code="manage_support_tickets", defaults={"name": "Manage Support Tickets"}
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


# ---------------------------------------------------------------------------
# Customer — Ticket CRUD
# ---------------------------------------------------------------------------

class CustomerTicketTest(TestCase):

    def setUp(self):
        self.customer = _user("+966500040001")
        self.client   = _bearer(self.customer)

    def test_create_ticket(self):
        resp = self.client.post(
            "/api/support/tickets/",
            {"subject": "My transfer failed", "body": "I tried to send USD 100.", "category": "PAYMENT_ISSUE"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["status"], TicketStatus.OPEN)

    def test_create_ticket_validation(self):
        resp = self.client.post("/api/support/tickets/", {"subject": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_list_own_tickets(self):
        create_ticket(user=self.customer, subject="T1", body="Body 1")
        create_ticket(user=self.customer, subject="T2", body="Body 2")
        resp = self.client.get("/api/support/tickets/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_cannot_list_other_users_tickets(self):
        other = _user("+966500040002")
        create_ticket(user=other, subject="Other ticket", body="Private body")
        resp = self.client.get("/api/support/tickets/")
        self.assertEqual(len(resp.json()), 0)

    def test_ticket_detail(self):
        t = create_ticket(user=self.customer, subject="Subj", body="Opening body")
        resp = self.client.get(f"/api/support/tickets/{t.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("messages", resp.json())
        self.assertEqual(len(resp.json()["messages"]), 1)

    def test_customer_reply(self):
        t = create_ticket(user=self.customer, subject="S", body="B")
        resp = self.client.post(f"/api/support/tickets/{t.pk}/reply/", {"body": "More info"}, format="json")
        self.assertEqual(resp.status_code, 201)

    def test_customer_close_ticket(self):
        t = create_ticket(user=self.customer, subject="S", body="B")
        resp = self.client.post(f"/api/support/tickets/{t.pk}/close/")
        self.assertEqual(resp.status_code, 200)
        t.refresh_from_db()
        self.assertEqual(t.status, TicketStatus.CLOSED)

    def test_unauthenticated_rejected(self):
        resp = APIClient().get("/api/support/tickets/")
        self.assertEqual(resp.status_code, 401)


# ---------------------------------------------------------------------------
# Internal notes not visible to customer
# ---------------------------------------------------------------------------

class InternalNoteVisibilityTest(TestCase):

    def setUp(self):
        self.customer     = _user("+966500040010")
        self.staff        = _staff_with_support_perm()
        self.customer_cli = _bearer(self.customer)
        self.staff_cli    = _bearer(self.staff)
        self.ticket = create_ticket(user=self.customer, subject="T", body="B")

    def test_internal_note_visible_to_staff(self):
        self.staff_cli.post(
            f"/api/staff/support/tickets/{self.ticket.pk}/reply/",
            {"body": "Secret note", "is_internal": True},
            format="json",
        )
        resp = self.staff_cli.get(f"/api/staff/support/tickets/{self.ticket.pk}/")
        messages = resp.json()["messages"]
        self.assertTrue(any(m["is_internal"] for m in messages))

    def test_internal_note_hidden_from_customer(self):
        self.staff_cli.post(
            f"/api/staff/support/tickets/{self.ticket.pk}/reply/",
            {"body": "Staff-only internal note", "is_internal": True},
            format="json",
        )
        resp = self.customer_cli.get(f"/api/support/tickets/{self.ticket.pk}/")
        messages = resp.json()["messages"]
        self.assertFalse(any(m["is_internal"] for m in messages))


# ---------------------------------------------------------------------------
# Customer — Notifications
# ---------------------------------------------------------------------------

class NotificationViewTest(TestCase):

    def setUp(self):
        self.user   = _user("+966500040020")
        self.client = _bearer(self.user)
        for i in range(3):
            dispatch_notification(
                user=self.user,
                notification_type=NotificationType.SYSTEM,
                title=f"Notif {i}",
                message=f"Msg {i}",
            )

    def test_list_notifications(self):
        resp = self.client.get("/api/support/notifications/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 3)

    def test_unread_filter(self):
        resp = self.client.get("/api/support/notifications/?unread=1")
        self.assertEqual(len(resp.json()), 3)

    def test_unread_count(self):
        resp = self.client.get("/api/support/notifications/unread-count/")
        self.assertEqual(resp.json()["unread_count"], 3)

    def test_mark_all_read(self):
        resp = self.client.post("/api/support/notifications/read-all/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["marked_read"], 3)
        # Unread count now 0
        resp2 = self.client.get("/api/support/notifications/?unread=1")
        self.assertEqual(len(resp2.json()), 0)

    def test_mark_one_read(self):
        notif = Notification.objects.filter(user=self.user).first()
        resp = self.client.post(f"/api/support/notifications/{notif.pk}/read/")
        self.assertEqual(resp.status_code, 200)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)


# ---------------------------------------------------------------------------
# Staff — Ticket management
# ---------------------------------------------------------------------------

class StaffTicketManagementTest(TestCase):

    def setUp(self):
        self.customer   = _user("+966500040030")
        self.staff      = _staff_with_support_perm()
        self.staff_cli  = _bearer(self.staff)
        self.ticket     = create_ticket(user=self.customer, subject="Issue X", body="Details here.")

    def test_staff_list_all_tickets(self):
        resp = self.staff_cli.get("/api/staff/support/tickets/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_staff_filter_by_status(self):
        resp = self.staff_cli.get("/api/staff/support/tickets/?status=OPEN")
        self.assertEqual(len(resp.json()), 1)
        resp2 = self.staff_cli.get("/api/staff/support/tickets/?status=RESOLVED")
        self.assertEqual(len(resp2.json()), 0)

    def test_staff_ticket_detail(self):
        resp = self.staff_cli.get(f"/api/staff/support/tickets/{self.ticket.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("messages", resp.json())

    def test_staff_assign(self):
        resp = self.staff_cli.post(f"/api/staff/support/tickets/{self.ticket.pk}/assign/")
        self.assertEqual(resp.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, TicketStatus.IN_PROGRESS)
        self.assertEqual(self.ticket.assigned_to, self.staff)

    def test_staff_resolve(self):
        resp = self.staff_cli.post(f"/api/staff/support/tickets/{self.ticket.pk}/resolve/")
        self.assertEqual(resp.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, TicketStatus.RESOLVED)

    def test_staff_close(self):
        resp = self.staff_cli.post(f"/api/staff/support/tickets/{self.ticket.pk}/close/")
        self.assertEqual(resp.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, TicketStatus.CLOSED)

    def test_staff_reply(self):
        resp = self.staff_cli.post(
            f"/api/staff/support/tickets/{self.ticket.pk}/reply/",
            {"body": "We are looking into it.", "is_internal": False},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_no_perm_blocked(self):
        no_perm_user = User.objects.create_user(
            phone_number="+966599999001", password="P!", status=UserStatus.ACTIVE,
            kyc_status=KycStatus.APPROVED,
        )
        client = _bearer(no_perm_user)
        resp = client.get("/api/staff/support/tickets/")
        self.assertEqual(resp.status_code, 403)
