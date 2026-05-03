"""Domain exceptions for the accounts app."""


class AccountNotFoundError(Exception):
    pass


class AccountRestrictedError(Exception):
    """Raised when a debit is attempted on a FROZEN / BLOCKED / CLOSED account."""
    pass


class InsufficientFundsError(Exception):
    """Raised when available_balance is insufficient for the requested debit."""
    pass


class BeneficiaryNotFoundError(Exception):
    pass


class BeneficiaryAlreadyExistsError(Exception):
    pass


class AccountAlreadyClosedError(Exception):
    pass


class CurrencyNotFoundError(Exception):
    pass
