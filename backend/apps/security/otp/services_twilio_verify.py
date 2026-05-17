from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings

from apps.security.models import OTPRequest
from apps.security.otp.clients.twilio_verify_client import TwilioVerifyClient, TwilioVerifyError
from apps.security.otp.services import create_otp, verify_otp
from apps.security.otp.policy import should_expose_dev_otp

if TYPE_CHECKING:
    from apps.users.models import User

logger = logging.getLogger(__name__)


class TwilioVerifyOTPService:
    """
    OTP service using Twilio Verify API.
    
    Features:
    - Managed OTP generation and delivery via Twilio Verify
    - Fallback to local OTP generation in dev mode if Twilio fails
    - Creates stub OTPRequest records for audit trail
    - Exposes OTP in dev mode only when using local fallback
    """
    
    def __init__(self):
        self._client = TwilioVerifyClient(
            account_sid=settings.TWILIO_ACCOUNT_SID,
            auth_token=settings.TWILIO_AUTH_TOKEN,
            service_sid=settings.TWILIO_VERIFY_SERVICE_SID,
        )
    
    def generate_otp(
        self,
        phone: str,
        request_type: str,
        user: User | None = None,
        purpose_reference: str = "",
        ip_address: str | None = None,
        device_id: str | None = None,
    ) -> dict:
        """
        Generate and send OTP via Twilio Verify.
        
        Flow:
        1. Generate local OTP for dev fallback
        2. Cancel any pending OTP requests
        3. Try to send via Twilio Verify
        4. If Twilio fails in dev mode, use local OTP
        5. Create OTPRequest record for audit trail
        6. Return OTP plain text only in dev fallback scenario
        
        Args:
            phone: Phone number in E.164 format
            request_type: Type of OTP request (LOGIN, PAYMENT, etc.)
            user: User instance if available
            purpose_reference: Reference ID for the request
            ip_address: IP address of the requester
            device_id: Device ID of the requester
            
        Returns:
            dict with success status and optional OTP plain text (dev mode only)
        """
        from apps.security.models import OTPRequest
        
        # 1. Generate local OTP first (for dev fallback)
        otp_plain, otp_hash, expires_at = create_otp()
        
        # Log OTP in dev mode for debugging
        if should_expose_dev_otp(request_type):
            logger.info(f"[OTP DEBUG] phone={phone} otp={otp_plain} type={request_type}")
        
        # 2. Cancel any pending OTP requests for this phone/type
        OTPRequest.objects.filter(
            phone_number=phone,
            purpose_reference=purpose_reference,
            request_type=request_type,
            status='PENDING',
        ).update(status='CANCELLED')
        
        # 3. Try to send via Twilio Verify
        twilio_success = False
        try:
            result = self._client.send_verification(
                to=phone, 
                channel="sms"
            )
            twilio_success = True
            otp_plain = None  # Don't expose OTP when Twilio succeeds
            logger.info(
                "Twilio Verify SMS sent successfully | phone=%s sid=%s",
                phone,
                result.get("sid")
            )
        except TwilioVerifyError as e:
            logger.warning(
                "Twilio Verify OTP send failed | phone=%s request_type=%s error=%s",
                phone,
                request_type,
                str(e)
            )
            # In production, raise the error
            if not settings.DEBUG:
                raise
            # In dev mode, continue with local OTP fallback
            logger.info(
                "Twilio Verify failed in dev mode | phone=%s - using local OTP fallback",
                phone
            )
        
        # 4. Create OTPRequest record for audit trail
        sent_via = 'TWILIO_VERIFY' if twilio_success else 'SMS'
        
        otp_request = OTPRequest.objects.create(
            user=user,
            phone_number=phone,
            request_type=request_type,
            purpose_reference=purpose_reference,
            otp_hash=otp_hash,
            status='PENDING',
            expires_at=expires_at,
            sent_via=sent_via,
            ip_address=ip_address,
            device_id=device_id,
        )
        
        # 5. Return response
        response = {
            "success": True,
            "message": "OTP sent successfully",
        }
        
        # Only expose OTP in dev mode when using local fallback
        if not twilio_success and should_expose_dev_otp(request_type) and otp_plain:
            response["otp"] = otp_plain
            response["dev_mode"] = True
        
        return response
    
    def verify_otp(
        self,
        phone: str,
        otp_code: str,
        request_type: str,
        purpose_reference: str = "",
    ) -> dict:
        """
        Verify OTP code.
        
        Flow:
        1. Find the OTP request
        2. If sent via Twilio Verify, verify with Twilio
        3. If Twilio verification fails in dev mode, fallback to local verification
        4. If sent via local SMS, verify locally
        5. Update OTP request status
        
        Args:
            phone: Phone number in E.164 format
            otp_code: OTP code to verify
            request_type: Type of OTP request
            purpose_reference: Reference ID for the request
            
        Returns:
            dict with verification result
            
        Raises:
            ValueError: If OTP is invalid or expired
        """
        from apps.security.models import OTPRequest
        
        # Find the OTP request
        try:
            otp_request = OTPRequest.objects.get(
                phone_number=phone,
                request_type=request_type,
                purpose_reference=purpose_reference,
                status='PENDING',
            )
        except OTPRequest.DoesNotExist:
            raise ValueError("No pending OTP request found")
        
        # Check if sent via Twilio Verify
        if otp_request.sent_via == 'TWILIO_VERIFY':
            try:
                result = self._client.check_verification(
                    to=phone,
                    code=otp_code
                )
                
                if result.get("valid"):
                    otp_request.status = 'VERIFIED'
                    otp_request.save()
                    logger.info(
                        "Twilio Verify OTP verified | phone=%s request_type=%s",
                        phone,
                        request_type
                    )
                    return {"success": True, "message": "OTP verified successfully"}
                else:
                    otp_request.attempts_count += 1
                    if otp_request.attempts_count >= otp_request.max_attempts:
                        otp_request.status = 'EXPIRED'
                    otp_request.save()
                    raise ValueError("Invalid OTP code")
                    
            except TwilioVerifyError as e:
                logger.warning(
                    "Twilio Verify check failed | phone=%s error=%s",
                    phone,
                    str(e)
                )
                # In production, raise the error
                if not settings.DEBUG:
                    raise ValueError("OTP verification failed")
                # In dev mode, fallback to local verification
                logger.info(
                    "Twilio Verify check failed in dev mode | phone=%s - using local verification",
                    phone
                )
        
        # Fallback to local verification (for local OTP or dev mode fallback)
        is_valid = verify_otp(otp_request.otp_hash, otp_code, otp_request.expires_at)
        
        if is_valid:
            otp_request.status = 'VERIFIED'
            otp_request.save()
            logger.info(
                "Local OTP verified | phone=%s request_type=%s",
                phone,
                request_type
            )
            return {"success": True, "message": "OTP verified successfully"}
        else:
            otp_request.attempts_count += 1
            if otp_request.attempts_count >= otp_request.max_attempts:
                otp_request.status = 'EXPIRED'
            otp_request.save()
            raise ValueError("Invalid or expired OTP code")
