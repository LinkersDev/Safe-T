# Twilio Verify OTP - Quick Start Guide

## 1. Get Twilio Credentials (5 minutes)

### Sign Up
1. Go to: https://www.twilio.com/try-twilio
2. Sign up for free trial account
3. Verify your email and phone

### Get Account Credentials
1. Go to Console Dashboard: https://console.twilio.com
2. Copy **Account SID** (starts with `AC...`)
3. Click "View" next to Auth Token
4. Copy **Auth Token**

### Create Verify Service
1. Go to: https://console.twilio.com/us1/develop/verify/services
2. Click **"Create new Service"**
3. Name it: `SafeT OTP`
4. Click **"Create"**
5. Copy **Service SID** (starts with `VA...`)

### Add Verified Phone Number (Trial Only)
1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/verified
2. Click **"Add a new Caller ID"**
3. Enter your test phone number (e.g., `+251912345678`)
4. Verify via SMS code

---

## 2. Configure Environment (2 minutes)

### Edit `.env` file:

```bash
# Change OTP provider
OTP_PROVIDER=twilio_verify

# Add Twilio credentials
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_VERIFY_SERVICE_SID=VAxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Keep DEBUG on for testing
DEBUG=True
```

**Replace:**
- `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx` with your Account SID
- `your_auth_token_here` with your Auth Token
- `VAxxxxxxxxxxxxxxxxxxxxxxxxxxxx` with your Verify Service SID

---

## 3. Restart Django Server (1 minute)

```bash
# Stop current server (Ctrl+C)

# Activate venv
.\venv\Scripts\Activate.ps1

# Start server
python manage.py runserver 0.0.0.0:8000
```

---

## 4. Test OTP Send (2 minutes)

### Using curl:

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+251912345678"}'
```

### Using Postman:

**Endpoint:** `POST http://localhost:8000/api/auth/login/`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "phone_number": "+251912345678"
}
```

### Expected Response:

```json
{
  "otp_request_id": 123,
  "otp_plain": null,
  "message": "OTP sent successfully"
}
```

### Expected Terminal Output:

```
[TWILIO VERIFY DEBUG] OTP sent to +251912345678 | SID: VExxxxxxxx
[TWILIO VERIFY DEBUG] Status: pending
```

### Expected SMS:

You should receive an SMS with a 6-digit code like:
```
Your SafeT OTP verification code is: 123456

Sent from a Twilio Trial Account
```

---

## 5. Test OTP Verification (1 minute)

### Using curl:

```bash
curl -X POST http://localhost:8000/api/auth/login/verify/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+251912345678", "otp": "123456"}'
```

### Using Postman:

**Endpoint:** `POST http://localhost:8000/api/auth/login/verify/`

**Body (JSON):**
```json
{
  "phone_number": "+251912345678",
  "otp": "123456"
}
```

### Expected Response (Success):

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "phone_number": "+251912345678",
    "full_name": "Test User",
    ...
  }
}
```

---

## 6. Test All OTP Flows

### Login OTP ✅
```bash
POST /api/auth/login/
POST /api/auth/login/verify/
```

### Registration OTP ✅
```bash
POST /api/auth/register/
POST /api/auth/register/verify/
```

### Password Reset OTP ✅
```bash
POST /api/auth/password-reset/request/
POST /api/auth/password-reset/verify/
```

### Transfer OTP ✅
```bash
POST /api/payments/transfers/
```

### QR Payment OTP ✅
```bash
POST /api/payments/qr/pay/
```

### Bill Payment OTP ✅
```bash
POST /api/payments/bills/pay/
```

---

## 7. Monitor Twilio Console

### Check Delivery Status:
1. Go to: https://console.twilio.com/us1/monitor/logs/verify
2. See all OTP sends and verifications
3. Check success/failure status
4. View error messages

### Check Usage:
1. Go to: https://console.twilio.com/us1/billing/usage
2. See SMS count
3. See costs (trial credit)

---

## Troubleshooting

### Issue: "Authentication Error"
**Fix:** Check Account SID and Auth Token in `.env`

### Issue: "Service not found"
**Fix:** Check Verify Service SID in `.env`

### Issue: "Permission denied"
**Fix:** Add phone number to Verified Caller IDs (trial only)

### Issue: OTP not received
**Fix:** 
1. Check Twilio console logs
2. Verify phone number format (+251...)
3. Check phone is verified (trial)

### Issue: "Invalid OTP"
**Fix:**
1. Check OTP code from SMS
2. OTP expires in 10 minutes
3. Try requesting new OTP

---

## Rollback to WhatsApp/Dev

**If Twilio fails, instant rollback:**

```bash
# In .env
OTP_PROVIDER=whatsapp  # or dev

# Restart server
# No code changes needed!
```

---

## Production Deployment

### Before Going Live:
1. ✅ Test all OTP flows
2. ✅ Upgrade Twilio account (remove trial limits)
3. ✅ Set `DEBUG=False`
4. ✅ Set `OTP_PROVIDER=twilio_verify`
5. ✅ Monitor costs in Twilio console

### Upgrade Twilio Account:
1. Go to: https://console.twilio.com/us1/billing
2. Add payment method
3. Upgrade account
4. Remove "Trial Account" message from SMS
5. Send to any phone number (not just verified)

---

## Environment Variables Summary

**Required:**
```bash
OTP_PROVIDER=twilio_verify
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_VERIFY_SERVICE_SID=VAxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Optional:**
```bash
DEBUG=True  # For development
ENABLE_DEV_OTP=True  # Not used by Twilio provider
```

---

## Success! 🎉

You now have:
- ✅ Twilio Verify OTP working
- ✅ Trial account compatible
- ✅ No phone number purchase needed
- ✅ Production-ready SMS delivery
- ✅ All OTP flows working
- ✅ Easy rollback to WhatsApp/Dev

**Total Setup Time:** ~10 minutes

**Next:** Test in production with real users!
