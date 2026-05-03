"""Enumerations and constants for the ledger app."""


class TransactionType:
    TRANSFER = "TRANSFER"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    QR_PAYMENT = "QR_PAYMENT"
    BILL_PAYMENT = "BILL_PAYMENT"

    CHOICES = [
        (TRANSFER, "Transfer"),
        (DEPOSIT, "Deposit"),
        (WITHDRAWAL, "Withdrawal"),
        (QR_PAYMENT, "QR Payment"),
        (BILL_PAYMENT, "Bill Payment"),
    ]


class TransactionStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"
    CANCELLED = "CANCELLED"

    CHOICES = [
        (PENDING, "Pending"),
        (PROCESSING, "Processing"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
        (REVERSED, "Reversed"),
        (CANCELLED, "Cancelled"),
    ]

    # Terminal states — a transaction in one of these cannot be re-processed
    TERMINAL: frozenset = frozenset({COMPLETED, FAILED, REVERSED, CANCELLED})


class EntryType:
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    FEE = "FEE"
    HOLD = "HOLD"
    RELEASE = "RELEASE"

    CHOICES = [
        (DEBIT, "Debit"),
        (CREDIT, "Credit"),
        (FEE, "Fee"),
        (HOLD, "Hold"),
        (RELEASE, "Release"),
    ]

    # Entry types that reduce the account's available balance
    DEBIT_TYPES: frozenset = frozenset({DEBIT, FEE, HOLD})
    # Entry types that increase the account's available balance
    CREDIT_TYPES: frozenset = frozenset({CREDIT, RELEASE})


class TransactionChannel:
    MOBILE = "MOBILE"
    API = "API"
    STAFF = "STAFF"
    SYSTEM = "SYSTEM"

    CHOICES = [
        (MOBILE, "Mobile App"),
        (API, "API"),
        (STAFF, "Staff Terminal"),
        (SYSTEM, "System"),
    ]


class FeeType:
    PERCENTAGE = "PERCENTAGE"
    FLAT = "FLAT"

    CHOICES = [
        (PERCENTAGE, "Percentage"),
        (FLAT, "Flat"),
    ]
