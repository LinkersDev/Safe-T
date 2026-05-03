"""Domain exceptions for the ledger app."""


class TransactionNotFoundError(Exception):
    pass


class DuplicateTransactionError(Exception):
    """Raised when an idempotency key matches an existing in-progress transaction."""
    pass


class TransactionBalanceError(Exception):
    """Raised when debit and credit totals do not balance — prevents commit."""
    pass


class TransactionAlreadyReversedError(Exception):
    pass


class TransactionNotReversibleError(Exception):
    """Raised when the transaction is not in COMPLETED status."""
    pass


class UserNotActiveError(Exception):
    """Raised when a PENDING_VERIFICATION user attempts a monetary operation."""
    pass


class KYCNotApprovedError(Exception):
    """
    Raised when a user whose kyc_status is not APPROVED attempts a financial
    operation via post_transaction().

    This is a defence-in-depth guard that runs even when the view layer has
    already checked IsKYCApproved, preventing direct service-layer bypasses.
    """
    pass
