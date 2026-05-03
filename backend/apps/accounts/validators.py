"""Validation helpers for the accounts app."""
from __future__ import annotations

from django.core.exceptions import ValidationError


def validate_account_number(value: str) -> str:
    """Strips whitespace and validates that the account number is 16 digits."""
    value = value.strip()
    if not value.isdigit() or len(value) != 16:
        raise ValidationError("Account number must be exactly 16 digits.")
    return value
