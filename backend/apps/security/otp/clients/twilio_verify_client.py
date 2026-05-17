from __future__ import annotations

import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


class TwilioVerifyError(Exception):
    """Raised when Twilio Verify operation fails."""
    pass


class TwilioVerifyClient:
    """
    Twilio Verify API client for managed OTP service.
    
    Twilio Verify handles:
    - OTP generation
    - OTP storage
    - SMS delivery
    - OTP verification
    
    No phone number purchase required (trial-compatible).
    """
    
    def __init__(self, account_sid: str, auth_token: str, service_sid: str):
        self.service_sid = service_sid
        self.client = Client(account_sid, auth_token)
        self.verify = self.client.verify.v2.services(service_sid)
    
    def send_verification(self, to: str, channel: str = "sms") -> dict:
        """
        Start verification (sends OTP via SMS).
        
        Args:
            to: Phone number in E.164 format (e.g., +251912345678)
            channel: Delivery channel ('sms' or 'call')
            
        Returns:
            dict with verification SID and status
            
        Raises:
            TwilioVerifyError: If sending fails
        """
        try:
            verification = self.verify.verifications.create(
                to=to,
                channel=channel
            )
            logger.info(
                "Twilio Verify OTP sent | to=%s sid=%s status=%s channel=%s",
                to,
                verification.sid,
                verification.status,
                channel
            )
            return {
                "sid": verification.sid,
                "status": verification.status,
                "to": verification.to,
                "channel": verification.channel,
            }
        except TwilioRestException as exc:
            logger.error(
                "Twilio Verify send failed | to=%s error_code=%s error_msg=%s",
                to,
                exc.code,
                exc.msg,
                exc_info=True
            )
            raise TwilioVerifyError(f"Twilio Verify error {exc.code}: {exc.msg}") from exc
    
    def check_verification(self, to: str, code: str) -> dict:
        """
        Verify OTP code.
        
        Args:
            to: Phone number in E.164 format
            code: OTP code to verify
            
        Returns:
            dict with verification status
            
        Raises:
            TwilioVerifyError: If verification fails or code is invalid
        """
        try:
            verification_check = self.verify.verification_checks.create(
                to=to,
                code=code
            )
            logger.info(
                "Twilio Verify check | to=%s status=%s valid=%s",
                to,
                verification_check.status,
                verification_check.valid
            )
            return {
                "status": verification_check.status,
                "valid": verification_check.valid,
                "to": verification_check.to,
            }
        except TwilioRestException as exc:
            logger.error(
                "Twilio Verify check failed | to=%s error_code=%s error_msg=%s",
                to,
                exc.code,
                exc.msg,
                exc_info=True
            )
            raise TwilioVerifyError(f"Twilio Verify error {exc.code}: {exc.msg}") from exc