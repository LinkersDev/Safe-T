"""Domain exceptions for the users app."""


class UserNotFoundError(Exception):
    pass


class PhoneAlreadyExistsError(Exception):
    pass


class UserNotActiveError(Exception):
    """Raised when an operation requires ACTIVE status but user is not active."""
    pass


class UserAlreadyApprovedError(Exception):
    pass


class InvalidApproverRoleError(Exception):
    """Raised when approver does not hold TELLER or ADMIN role."""
    pass
