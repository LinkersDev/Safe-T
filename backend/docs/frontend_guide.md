# SafeT Backend — Frontend Integration Guide

This guide is written for the mobile / web frontend team. It covers everything
you need to integrate with the SafeT backend API.

---

## 1. Base Setup

### Base URL
```
Development : http://localhost:8000
Production  : https://api.safet.app  (update once deployed)
```

### Required Headers
Every API call must include:
```
Content-Type: application/json
```

For authenticated endpoints, additionally:
```
Authorization: Bearer <access_token>
```

### Important: Token Expiry
| Token | Lifetime | Action on expiry |
|---|---|---|
| Access token | 15 minutes | Call `/api/auth/token/refresh/` |
| Refresh token | 7 days | Redirect user to login |

---

## 2. Authentication Flow

### 2.1 Registration (4 steps)

```
Step 1: Request OTP
POST /api/auth/register/
{ "phone_number": "+966500000001" }
→ 200 { "detail": "OTP sent to +966500000001" }

Step 2: Verify OTP
POST /api/auth/register/verify-otp/
{ "phone_number": "+966500000001", "otp": "123456" }
→ 200 { "detail": "OTP verified." }

Step 3: Complete Registration
POST /api/auth/register/complete/
{ "phone_number": "+966500000001", "password": "SecurePass1!", "full_name": "Ali Hassan" }
→ 201 { "detail": "Registration complete. Awaiting staff approval." }

Step 4: Wait for staff approval
→ User status becomes ACTIVE when approved
→ A bank account is automatically created on approval
```

**Important:** After registration, the user is `PENDING_VERIFICATION`. They cannot
log in or make transactions until a staff member approves them.

### 2.2 Login Flow (3 steps)

```
Step 1: Request OTP
POST /api/auth/otp/send/
{ "phone_number": "+966500000001" }
→ 200 { "detail": "OTP sent." }

Step 2: Login
POST /api/auth/login/
{
  "phone_number": "+966500000001",
  "password": "SecurePass1!",
  "otp": "654321",
  "device_id": "unique-device-uuid",
  "device_name": "iPhone 15 Pro"
}
→ 200 {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGci...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGci...",
    "user": { "id": 1, "full_name": "Ali Hassan", "status": "ACTIVE" }
  }

Step 3: Store tokens securely
→ Store access token in memory (not localStorage)
→ Store refresh token in HttpOnly cookie or secure storage
```

### 2.3 Token Refresh

```
POST /api/auth/token/refresh/
{ "refresh": "eyJ..." }
→ 200 {
    "access": "eyJ... (new)",
    "refresh": "eyJ... (rotated)"
  }
```

**Implement auto-refresh:** Before any API call, check if the access token is
about to expire (< 60 seconds remaining). If so, refresh it first.

```javascript
// Example: decode JWT to check expiry
const payload = JSON.parse(atob(token.split('.')[1]));
const expiresIn = payload.exp - Math.floor(Date.now() / 1000);
if (expiresIn < 60) {
  await refreshTokens();
}
```

---

## 3. Error Handling

### Standard Error Format
All errors return JSON with a `detail` field:
```json
{ "detail": "Authentication credentials were not provided." }
```

For validation errors, use the `errors` object:
```json
{
  "errors": {
    "phone_number": ["This field is required."],
    "amount": ["Ensure this value is greater than or equal to 0.01."]
  }
}
```

### HTTP Status Codes

| Code | Meaning | Frontend Action |
|---|---|---|
| 200 | Success | Process response |
| 201 | Created | Show success, update list |
| 400 | Bad Request | Show field-level errors |
| 401 | Unauthorised | Redirect to login |
| 403 | Forbidden | Show specific message (KYC, permission) |
| 404 | Not Found | Show "not found" screen |
| 409 | Conflict | Show conflict message (e.g., "already submitted") |
| 429 | Rate Limited | Show "too many attempts, wait N seconds" |
| 500 | Server Error | Show generic error, report to monitoring |

### Common 403 Messages to Handle
```json
{ "detail": "Your identity verification (KYC) is not yet approved. Please upload your documents and wait for staff review." }
{ "detail": "Your account is not active." }
{ "detail": "Permission required: review_fraud_alert" }
```

---

## 4. KYC Flow

A user must complete KYC before making any financial transactions.

```
Check status
GET /api/kyc/status/
→ { "kyc_status": "NOT_SUBMITTED", "documents": [] }

Upload document
POST /api/kyc/upload/
Content-Type: multipart/form-data
  document_type=NATIONAL_ID
  file=<image>
→ { "id": 1, "status": "PENDING" }
→ User kyc_status becomes "PENDING"

Staff reviews → APPROVED or REJECTED

On REJECTED: user can re-upload
POST /api/kyc/upload/  (again)
→ kyc_status → PENDING again

On APPROVED: user can make transfers
```

**KYC Status Values:**
- `NOT_SUBMITTED` — user hasn't uploaded any documents
- `PENDING` — documents uploaded, awaiting review
- `APPROVED` — verified, all financial operations enabled
- `REJECTED` — rejected, user should re-upload

---

## 5. Transfer Flow (Full)

```
Step 1: Check balance
GET /api/accounts/
→ Get source account id and available_balance

Step 2: Request OTP
POST /api/payments/transfer/otp/
{ "account_id": 1, "amount": "500.00" }
→ 200 { "detail": "OTP sent." }

Step 3: Execute transfer
POST /api/payments/transfer/
{
  "source_account_id": 1,
  "destination_account_number": "6000000000000002",
  "amount": "500.00",
  "currency": "SAR",
  "otp": "654321",
  "description": "Rent payment",
  "idempotency_key": "generate-unique-uuid-per-attempt"
}
→ 200 {
    "reference_number": "TXN2024000001",
    "status": "COMPLETED",
    "amount": "500.00",
    "fee": "5.00",
    "occurred_at": "2024-01-15T10:30:00Z"
  }
```

**Important — Idempotency Key:**
Generate a unique UUID for each transfer attempt. If the network fails and
the user retries, use the **same idempotency_key**. The server will return
the original transaction instead of processing it twice.

```javascript
// Generate before showing the confirmation screen
const idempotencyKey = crypto.randomUUID();
// Store it; reuse on retry; clear after success
```

**Error cases to handle:**
```json
{ "detail": "Insufficient funds." }                           // 400
{ "detail": "Destination account not found." }               // 404
{ "detail": "Source account is frozen." }                    // 400
{ "detail": "Your identity verification (KYC) is not yet approved." }  // 403
```

---

## 6. QR Payment Flow (Full)

### As Merchant (generating QR)

```
POST /api/merchant/qr/generate/
{ "amount_mode": "FIXED", "display_amount": "250.00", "currency": "SAR" }
→ {
    "qr_token": "tok_abc123xyz...",
    "qr_payload": "safet://pay?token=tok_abc123xyz",
    "expires_at": "2024-01-15T11:30:00Z"
  }

Display the qr_payload as a QR code image to the customer.
```

### As Customer (paying via QR)

```
Step 1: Scan QR → extract token

Step 2: Resolve QR details
GET /api/payments/qr/{token}/
→ {
    "qr_token": "tok_abc123xyz",
    "merchant_name": "Coffee Shop",
    "amount": "250.00",
    "currency": "SAR",
    "status": "PENDING"
  }

Step 3: Request OTP
POST /api/payments/qr/otp/
{ "qr_token": "tok_abc123xyz", "payer_account_id": 1 }
→ 200 { "detail": "OTP sent." }

Step 4: Execute payment
POST /api/payments/qr/pay/
{
  "qr_token": "tok_abc123xyz",
  "payer_account_id": 1,
  "amount": "250.00",
  "otp": "789012",
  "idempotency_key": "uuid-xyz789"
}
→ 200 {
    "reference_number": "TXN2024000002",
    "status": "COMPLETED",
    "amount": "250.00"
  }
```

**Error cases:**
```json
{ "detail": "QR code has expired." }                         // 400
{ "detail": "QR code has already been paid." }               // 400
{ "detail": "Only one payment per QR code is allowed." }     // 409
```

---

## 7. Bill Payment Flow (Full)

```
Step 1: List providers
GET /api/payments/bill/providers/
→ [
    { "code": "WATER_001", "name": "Water Authority", "service_type": "WATER" },
    { "code": "ELECTRIC_001", "name": "National Grid", "service_type": "ELECTRICITY" }
  ]

Step 2: Fetch bill amount
POST /api/payments/bill/fetch/
{ "provider_code": "WATER_001", "service_number": "12345678" }
→ {
    "provider_name": "Water Authority",
    "service_number": "12345678",
    "bill_reference": "BIL-2024-001",
    "amount": "120.00",
    "due_date": "2024-01-31"
  }

Step 3: Request OTP
POST /api/payments/bill/otp/
{ "provider_code": "WATER_001", "service_number": "12345678", "payer_account_id": 1 }
→ 200 { "detail": "OTP sent." }

Step 4: Execute payment
POST /api/payments/bill/pay/
{
  "provider_code": "WATER_001",
  "service_number": "12345678",
  "payer_account_id": 1,
  "amount": "120.00",
  "otp": "345678",
  "idempotency_key": "uuid-bill001"
}
→ 200 {
    "reference_number": "TXN2024000003",
    "status": "COMPLETED",
    "biller_amount": "120.00",
    "fee_amount": "2.00",
    "paid_at": "2024-01-15T10:45:00Z"
  }
```

---

## 8. Notification Polling

After any financial transaction completes, the user receives in-app notifications.

```
Poll unread count (e.g. every 30 seconds)
GET /api/support/notifications/unread-count/
→ { "unread_count": 3 }

Fetch notifications
GET /api/support/notifications/
→ [
    {
      "id": 10,
      "notification_type": "TRANSACTION_RECEIVED",
      "title": "Money Received",
      "body": "You received SAR 500.00",
      "is_read": false,
      "created_at": "..."
    }
  ]

Mark read
PATCH /api/support/notifications/10/read/
→ 200 { "id": 10, "is_read": true }

Mark all read
POST /api/support/notifications/mark-all-read/
→ 200 { "detail": "All notifications marked as read." }
```

**Notification types:**
- `TRANSACTION_SENT` — debit completed
- `TRANSACTION_RECEIVED` — credit received
- `TICKET_REPLY` — support agent replied

---

## 9. Support Tickets

```
Create ticket
POST /api/support/tickets/
{ "subject": "Transfer not received", "category": "PAYMENT", "message": "..." }
→ { "id": 5, "status": "OPEN", "created_at": "..." }

List tickets
GET /api/support/tickets/
→ [{ "id": 5, "subject": "...", "status": "OPEN", "updated_at": "..." }]

Add reply
POST /api/support/tickets/5/reply/
{ "message": "I can attach the screenshot." }

Close ticket (customer)
POST /api/support/tickets/5/close/
```

---

## 10. Security Best Practices (Frontend)

1. **Never store JWTs in localStorage** — use memory + HttpOnly cookies.
2. **Always use idempotency keys** for all financial operations.
3. **Show loading state** during OTP requests (server enforces 3/10min rate limit).
4. **Handle 401 automatically** — intercept responses and trigger token refresh.
5. **Validate amount on client** before sending (must be > 0, max 2 decimal places).
6. **Do not cache sensitive responses** (account balances, transaction details).
7. **Obfuscate device UUID** but keep it stable across app sessions.
8. **KYC gate** — check `user.kyc_status` before showing transfer/payment screens;
   show upload prompt if `NOT_SUBMITTED` or `REJECTED`.
