"""Enumerations and constants for the payments app."""


class MerchantStatus:
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"

    CHOICES = [
        (ACTIVE, "Active"),
        (SUSPENDED, "Suspended"),
        (CLOSED, "Closed"),
    ]


class QRAmountMode:
    FIXED = "FIXED"    # Merchant sets amount at QR generation time
    OPEN = "OPEN"      # Payer enters the amount at scan time

    CHOICES = [
        (FIXED, "Fixed Amount"),
        (OPEN, "Open Amount"),
    ]


class QRPaymentStatus:
    PENDING = "PENDING"      # Generated, awaiting payment
    PAID = "PAID"            # Successfully paid
    EXPIRED = "EXPIRED"      # TTL elapsed
    CANCELLED = "CANCELLED"  # Merchant cancelled

    CHOICES = [
        (PENDING, "Pending"),
        (PAID, "Paid"),
        (EXPIRED, "Expired"),
        (CANCELLED, "Cancelled"),
    ]


# QR token validity in hours
QR_TOKEN_TTL_HOURS = 24
