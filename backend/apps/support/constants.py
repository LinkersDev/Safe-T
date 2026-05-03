"""String choices for the support app."""


class TicketStatus:
    OPEN        = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED    = "RESOLVED"
    CLOSED      = "CLOSED"

    CHOICES = [
        (OPEN,        "Open"),
        (IN_PROGRESS, "In Progress"),
        (RESOLVED,    "Resolved"),
        (CLOSED,      "Closed"),
    ]

    # Statuses that accept new messages
    ACTIVE_STATUSES = {OPEN, IN_PROGRESS}


class TicketCategory:
    ACCOUNT_ISSUE  = "ACCOUNT_ISSUE"
    PAYMENT_ISSUE  = "PAYMENT_ISSUE"
    KYC_ISSUE      = "KYC_ISSUE"
    CARD_ISSUE     = "CARD_ISSUE"
    GENERAL        = "GENERAL"
    OTHER          = "OTHER"

    CHOICES = [
        (ACCOUNT_ISSUE, "Account Issue"),
        (PAYMENT_ISSUE, "Payment Issue"),
        (KYC_ISSUE,     "KYC Issue"),
        (CARD_ISSUE,    "Card Issue"),
        (GENERAL,       "General Inquiry"),
        (OTHER,         "Other"),
    ]


class NotificationType:
    # Financial
    TRANSACTION_SENT     = "TRANSACTION_SENT"
    TRANSACTION_RECEIVED = "TRANSACTION_RECEIVED"
    # Support
    TICKET_OPENED        = "TICKET_OPENED"
    TICKET_REPLIED       = "TICKET_REPLIED"
    TICKET_RESOLVED      = "TICKET_RESOLVED"
    # KYC
    KYC_APPROVED         = "KYC_APPROVED"
    KYC_REJECTED         = "KYC_REJECTED"
    # System
    SYSTEM               = "SYSTEM"

    CHOICES = [
        (TRANSACTION_SENT,     "Transaction Sent"),
        (TRANSACTION_RECEIVED, "Transaction Received"),
        (TICKET_OPENED,        "Support Ticket Opened"),
        (TICKET_REPLIED,       "Support Ticket Replied"),
        (TICKET_RESOLVED,      "Support Ticket Resolved"),
        (KYC_APPROVED,         "KYC Approved"),
        (KYC_REJECTED,         "KYC Rejected"),
        (SYSTEM,               "System Message"),
    ]
