"""
OTP generation and verification utilities.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from argon2 import PasswordHasher
from django.utils import timezone

# Argon2 hasher for OTP
ph = PasswordHasher()


def create_otp(length: int = 6, expiry_minutes: int = 5) -> tuple[str, str, datetime]:
    """
    Generate a random OTP code and its hash.
    
    Args:
        length: Length of OTP code (default 6 digits)
        expiry_minutes: Minutes until OTP expires (default 5)
        
    Returns:
        Tuple of (otp_plain, otp_hash, expires_at)
    """
    # Generate random numeric OTP
    otp_plain = ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    # Hash the OTP
    otp_hash = ph.hash(otp_plain)
    
    # Calculate expiry time
    expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
    
    return otp_plain, otp_hash, expires_at


def verify_otp(otp_hash: str, otp_plain: str, expires_at: datetime) -> bool:
    """
    Verify an OTP code against its hash.
    
    Args:
        otp_hash: Hashed OTP from database
        otp_plain: Plain OTP code to verify
        expires_at: Expiry datetime
        
    Returns:
        True if OTP is valid and not expired, False otherwise
    """
    # Check if expired
    if timezone.now() > expires_at:
        return False
    
    # Verify hash
    try:
        ph.verify(otp_hash, otp_plain)
        return True
    except Exception:
        return False
