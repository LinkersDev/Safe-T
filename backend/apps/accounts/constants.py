"""Enumerations and constants for the accounts app."""


class AccountStatus:
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    BLOCKED = "BLOCKED"
    CLOSED = "CLOSED"

    CHOICES = [
        (ACTIVE, "Active"),
        (FROZEN, "Frozen"),
        (BLOCKED, "Blocked"),
        (CLOSED, "Closed"),
    ]

    # Any of these statuses prevents the account from originating a debit
    DEBIT_RESTRICTED: frozenset = frozenset({FROZEN, BLOCKED, CLOSED})


class RestrictionType:
    FREEZE = "FREEZE"
    BLOCK = "BLOCK"

    CHOICES = [
        (FREEZE, "Freeze"),
        (BLOCK, "Block"),
    ]


class RestrictionSource:
    RISK_OFFICER = "RISK_OFFICER"
    ADMIN = "ADMIN"
    COMPLIANCE = "COMPLIANCE"
    AUTO = "AUTO"

    CHOICES = [
        (RISK_OFFICER, "Risk Officer"),
        (ADMIN, "Admin"),
        (COMPLIANCE, "Compliance"),
        (AUTO, "Auto"),
    ]


# Default currency applied on account creation
DEFAULT_CURRENCY_CODE = "USD"

# Account number is 16 numeric digits
ACCOUNT_NUMBER_LENGTH = 16

# Seed currencies: (code, name, symbol, decimal_places)
SEED_CURRENCIES = [
    ("USD", "US Dollar", "$", 2),
    ("EUR", "Euro", "€", 2),
]
