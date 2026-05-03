"""Domain exceptions for the risk app."""


class AlertNotFoundError(Exception):
    pass


class AlertAlreadyReviewedError(Exception):
    """Raised when a Risk Officer tries to review an already-closed alert."""
    pass
