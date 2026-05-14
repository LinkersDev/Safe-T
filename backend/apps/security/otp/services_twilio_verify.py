from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.security.otp.clients.twilio_verify_client import (
    TwilioVerifyClient,
    TwilioVerifyError,
)
from apps.security.otp.interfaces import OTPIssueResult
from apps.security.otp.policy import should_expose_dev_otp
from apps.security.constants import OTPStatus
from apps.security.models import OTPRequest
from apps.security.services import create_otp, verify_otp
from apps.security.exceptions import (
    OTPInvalidError,
    OTPNotFoundError,
)

logger = logging.getLogger(__name__)


class TwilioVerifyOTPService:
    """
    Production OTP service using Twilio Verify managed OTP.
    
    IMPORTANT DIFFERENCES FROM OTHER PROVIDERS:
    * Does NOT use create_otp() - Twilio generates the OTP
    * Does NOT use verify_otp() - Twilio verifies the OTP
    * Creates stub OTPRequest records for audit trail only
    * No phone number purchase required (trial-compatible)
    
    Twilio Verify handles:
    - OTP generation (6-digit code)
    - OTP storage (on Twilio's servers)
    - SMS delivery
    - OTP verification
    - Expiration (10 minutes default)
    """
    
    def __init__(self, client: TwilioVerifyClient | None = None):
        if client is None:
            client = TwilioVerifyClient(
                account_sid=settings.TWILIO_ACCOUNT_SID,
                auth_token=settings.TWILIO_AUTH_TOKEN,
                service_sid=settings.TWILIO_VERIFY_SERVICE_SID,
            )
        self._client = client
    
    def generate_otp(
        self,
        *,
        phone: str,
        request_type: str,
        purpose_ref: str = "",
        ip: str | None = None,
        device_id: str = "",
        user=None,
    ) -> OTPIssueResult:
        """
        Generate and send OTP via Twilio Verify.
        
        In dev mode: Falls back to local OTP if Twilio fails.
        In production: Requires Twilio to succeed.
        """
        # 1. Generate local OTP first (for dev fallback)
        otp, otp_plain = create_otp(
            phone=phone,
            request_type=request_type,
            purpose_ref=purpose_ref,
            ip=ip,
            device_id=device_id,
            user=user,
        )
        
        # 2. Dev-only terminal exposure (BEFORE sending SMS)
        if settings.DEBUG and should_expose_dev_otp(request_type):
            print(f"[TWILIO DEV] OTP for {phone}: {otp_plain}")
        
        # 3. Try to send via Twilio Verify with custom message
        twilio_success = False
        custom_message = "Welcome to SaFe-T! Your OTP code is: {{CODE}}"
        try:
            result = self._client.send_verification(
                to=phone, 
                channel="sms",
                custom_message=custom_message
            )
            twilio_success = True
            logger.info(
                "Twilio Verify OTP sent | phone=%s request_type=%s sid=%s",
                phone,
                request_type,
                result.get("sid"),
            )
            if settings.DEBUG:
                print(f"[TWILIO VERIFY] SMS sent successfully | SID: {result.get('sid')}")
        except TwilioVerifyError as exc:
            logger.error(
                "Twilio Verify OTP send failed | phone=%s request_type=%s error=%s",
                phone,
                request_type,
                exc,
                exc_info=True,
            )
            if settings.DEBUG:
                print(f"[TWILIO VERIFY ERROR] Failed to send SMS to {phone}")
                print(f"[TWILIO VERIFY ERROR] Error: {exc}")
                print(f"[TWILIO VERIFY FALLBACK] Using local OTP: {otp_plain}")
                # In dev mode, continue with local OTP
            else:
                # In production, fail the request
                raise
        
        # 4. Update OTP record with Twilio status
        if twilio_success:
            otp.sent_via = "TWILIO_VERIFY"
            otp.save(update_fields=["sent_via"])
        
        # 5. Return result - expose OTP in dev mode if Twilio failed
        return OTPIssueResult(
            otp_request_id=otp.pk,
            otp_plain=otp_plain if (settings.DEBUG and should_expose_dev_otp(request_type)) else None,
        )
    
    def verify_otp(
        self,
        *,
        phone: str,
        request_type: str,
        otp_plain: str,
        purpose_ref: str = "",
    ):
        """
        Verify OTP via Twilio Verify or local verification.
        
        Tries Twilio first, falls back to local verification if Twilio sent_via != TWILIO_VERIFY.
        """
        # 1. Find the pending OTP request
        try:
            otp_request = OTPRequest.objects.filter(
                phone_number=phone,
                request_type=request_type,
                purpose_reference=purpose_ref,
                status=OTPStatus.PENDING,
            ).latest("created_at")
        except OTPRequest.DoesNotExist:
            logger.warning(
                "OTP not found | phone=%s request_type=%s",
                phone,
                request_type,
            )
            raise OTPNotFoundError("No pending OTP request found")
        
        # 2. Check if this was sent via Twilio Verify
        if otp_request.sent_via == "TWILIO_VERIFY":
            # Verify with Twilio
            try:
                result = self._client.check_verification(to=phone, code=otp_plain)
                
                if not result.get("valid"):
                    # Invalid OTP
                    otp_request.attempts_count += 1
                    otp_request.save(update_fields=["attempts_count"])
                    logger.warning(
                        "Twilio Verify OTP invalid | phone=%s request_type=%s attempts=%d",
                        phone,
                        request_type,
                        otp_request.attempts_count,
                    )
                    raise OTPInvalidError("Invalid OTP code")
                
                # Valid OTP
                otp_request.status = OTPStatus.VERIFIED
                otp_request.verified_at = timezone.now()
                otp_request.save(update_fields=["status", "verified_at"])
                
                logger.info(
                    "Twilio Verify OTP verified | phone=%s request_type=%s otp_request_id=%s",
                    phone,
                    request_type,
                    otp_request.pk,
                )
                
                return otp_request
                
            except TwilioVerifyError as exc:
                # Twilio error - fall back to local verification in dev mode
                if settings.DEBUG:
                    logger.warning(
                        "Twilio Verify check failed, falling back to local | phone=%s error=%s",
                        phone,
                        exc,
                    )
                    print(f"[TWILIO VERIFY FALLBACK] Using local verification")
                    return verify_otp(
                        phone=phone,
                        request_type=request_type,
                        otp_plain=otp_plain,
                        purpose_ref=purpose_ref,
                    )
                else:
                    # Production - fail
                    otp_request.attempts_count += 1
                    otp_request.save(update_fields=["attempts_count"])
                    raise OTPInvalidError(f"OTP verification failed: {exc}")
        else:
            # Not sent via Twilio - use local verification
            return verify_otp(
                phone=phone,
                request_type=request_type,
                otp_plain=otp_plain,
                purpose_ref=purpose_ref,
            )
