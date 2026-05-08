# OTP Refactor — Applied Changes

## Checklist

- [x] `OTP_EXPIRY_MINUTES` increased 3 → 5 in `backend/apps/security/constants.py`
- [x] Dev OTP exposure now requires `ENABLE_DEV_OTP=True` (no longer implicit via `DEBUG`)
- [x] Added `OTPSendPhoneThrottle` — 3 OTP requests per hour per phone number
- [x] `OTPRequest.max_attempts` model default set to 3; `create_otp` now explicitly passes `max_attempts=OTP_MAX_ATTEMPTS`
- [x] Added `purpose_ref="TRANSFER"` to `send_transfer_otp`
- [x] Applied `@throttle_classes([OTPSendThrottle, OTPSendPhoneThrottle])` to all OTP send endpoints:
  - Security: registration, login, first-login, password-reset, PIN-reset
  - Payments: transfer, QR payment, bill payment
- [x] Added secure OTP debug logging (logs only, no API exposure)

## TODO

- [ ] Run `python manage.py makemigrations` to generate migration for `OTPRequest.max_attempts` default change
- [ ] Add `DEFAULT_THROTTLE_RATES['otp_send_phone'] = '3/h'` in Django settings for production
