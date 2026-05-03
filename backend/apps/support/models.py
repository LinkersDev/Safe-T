"""Support app models: SupportTicket, SupportTicketMessage, Notification."""
from django.conf import settings
from django.db import models

from .constants import NotificationType, TicketCategory, TicketStatus


class SupportTicket(models.Model):
    """
    Customer-raised support ticket.

    Lifecycle: OPEN → IN_PROGRESS (staff picks up) → RESOLVED / CLOSED
    Staff replies via SupportTicketMessage; internal notes are staff-only.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )
    subject = models.CharField(max_length=200)
    category = models.CharField(
        max_length=30, choices=TicketCategory.CHOICES, default=TicketCategory.GENERAL
    )
    status = models.CharField(
        max_length=20, choices=TicketStatus.CHOICES, default=TicketStatus.OPEN, db_index=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at   = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_tickets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"], name="support_ticket_user_status_idx"),
            models.Index(fields=["status"],          name="support_ticket_status_idx"),
            models.Index(fields=["assigned_to"],     name="support_ticket_assignee_idx"),
        ]

    def __str__(self) -> str:
        return f"Ticket#{self.pk} [{self.status}] {self.subject[:40]}"


class SupportTicketMessage(models.Model):
    """
    A single message or note on a support ticket.

    `is_internal=True` messages are staff-only notes not visible to the customer.
    """
    ticket     = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    sender     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="support_messages"
    )
    body       = models.TextField()
    is_internal = models.BooleanField(
        default=False,
        help_text="If True, visible to staff only (internal note).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "support_ticket_messages"
        ordering = ["created_at"]

    def __str__(self) -> str:
        internal = " [INTERNAL]" if self.is_internal else ""
        return f"Msg#{self.pk} Ticket#{self.ticket_id}{internal}"


class Notification(models.Model):
    """
    In-app notification for a user.

    Created by:
      - post_transaction on_commit hook  (TRANSACTION_SENT / TRANSACTION_RECEIVED)
      - Support ticket events            (TICKET_OPENED / TICKET_REPLIED / TICKET_RESOLVED)
      - KYC status changes               (KYC_APPROVED / KYC_REJECTED)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=40, choices=NotificationType.CHOICES, db_index=True
    )
    title   = models.CharField(max_length=200)
    message = models.TextField()

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Optional reference back to the source object
    reference_type = models.CharField(max_length=50, blank=True)  # "transaction", "ticket", etc.
    reference_id   = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"], name="notif_user_read_idx"),
        ]

    def __str__(self) -> str:
        return f"Notif#{self.pk} [{self.notification_type}] user={self.user_id}"
