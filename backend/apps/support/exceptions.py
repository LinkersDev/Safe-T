"""Domain exceptions for the support app."""


class TicketNotFoundError(Exception):
    pass


class TicketClosedError(Exception):
    """Raised when an operation is attempted on a CLOSED/RESOLVED ticket."""
    pass


class NotificationNotFoundError(Exception):
    pass


class UnauthorizedTicketAccessError(Exception):
    """Raised when a user tries to access a ticket they do not own."""
    pass
