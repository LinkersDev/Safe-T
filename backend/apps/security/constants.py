"""Enumerations for the security app."""


class OTPRequestType:
    REGISTRATION = "REGISTRATION"
    LOGIN = "LOGIN"
    FIRST_LOGIN = "FIRST_LOGIN"
    TRANSFER = "TRANSFER"
    QR_PAYMENT = "QR_PAYMENT"
    BILL_PAYMENT = "BILL_PAYMENT"
    PASSWORD_RESET = "PASSWORD_RESET"
    PIN_RESET = "PIN_RESET"
    DEVICE_BIND = "DEVICE_BIND"

    CHOICES = [
        (REGISTRATION, "Registration"),
        (LOGIN, "Login"),
        (FIRST_LOGIN, "First Login"),
        (TRANSFER, "Transfer"),
        (QR_PAYMENT, "QR Payment"),
        (BILL_PAYMENT, "Bill Payment"),
        (PASSWORD_RESET, "Password Reset"),
        (PIN_RESET, "PIN Reset"),
        (DEVICE_BIND, "Device Bind"),
    ]


class OTPStatus:
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

    CHOICES = [
        (PENDING, "Pending"),
        (VERIFIED, "Verified"),
        (FAILED, "Failed"),
        (EXPIRED, "Expired"),
        (CANCELLED, "Cancelled"),
    ]


class LoginStatus:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

    CHOICES = [
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
    ]


class LockEventType:
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"

    CHOICES = [
        (LOCKED, "Locked"),
        (UNLOCKED, "Unlocked"),
    ]


class ResetType:
    PASSWORD = "PASSWORD"
    PIN = "PIN"

    CHOICES = [
        (PASSWORD, "Password"),
        (PIN, "PIN"),
    ]


# Number of failed login/OTP attempts before auto-lock
MAX_FAILED_LOGIN_ATTEMPTS = 5
# Window in minutes to count failures
FAILED_LOGIN_WINDOW_MINUTES = 30
# OTP validity in minutes
OTP_EXPIRY_MINUTES = 3
# Max OTP attempts before marking FAILED
OTP_MAX_ATTEMPTS = 3
