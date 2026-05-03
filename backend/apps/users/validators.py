"""
Domain validation helpers for users.
"""
import phonenumbers


def normalize_phone(phone: str) -> str:
    """
    Parse and normalise a phone number to E.164 format.
    Raises ValueError if the number is invalid.
    """
    try:
        parsed = phonenumbers.parse(phone, None)
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError(f"Invalid phone number: {phone}")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        raise ValueError(f"Cannot parse phone number: {phone}")
