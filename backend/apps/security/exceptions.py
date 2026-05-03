"""Domain exceptions for the security app."""


class OTPNotFoundError(Exception):
    pass


class OTPExpiredError(Exception):
    pass


class OTPInvalidError(Exception):
    pass


class OTPMaxAttemptsExceededError(Exception):
    pass


class UserLockedError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass
