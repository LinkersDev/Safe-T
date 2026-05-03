# SafeT Backend — System Workflows

Detailed step-by-step flows for every critical operation.

---

## 1. User Registration

```
┌─────────────────────────────────────────────────────────────────────┐
│  CUSTOMER                          BACKEND                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  POST /register/              →   Generate OTP (argon2 hash)       │
│    { phone_number }           ←   Store OTPRequest (PENDING)       │
│                               ←   "OTP sent"                       │
│                                                                     │
│  POST /register/verify-otp/  →   Load OTPRequest by phone          │
│    { phone, otp }             →   argon2.verify(otp, stored_hash)   │
│                               →   Check expiry (10 min)            │
│                               →   Increment attempts_count          │
│                               →   Max 3 attempts → EXPIRED          │
│                               ←   OTPRequest.status = VERIFIED     │
│                               ←   "OTP verified"                   │
│                                                                     │
│  POST /register/complete/     →   Check OTPRequest.status=VERIFIED  │
│    { phone, password, name }  →   Hash password (argon2)           │
│                               →   Create User (PENDING_VERIFICATION)│
│                               ←   "Awaiting staff approval"        │
│                                                                     │
│  [STAFF APPROVES USER]                                              │
│                                                                     │
│  POST /staff/users/{id}/approve/  →  User.status = ACTIVE          │
│                                   →  Create Account (SAR)          │
│                               ←   { status: "ACTIVE" }             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key invariants:**
- OTP expires after 10 minutes
- Maximum 3 verification attempts before OTP is invalidated
- Account is only created after staff approves the user
- Phone number uniqueness is enforced at the database level

---

## 2. Login

```
┌─────────────────────────────────────────────────────────────────────┐
│  CUSTOMER                          BACKEND                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  POST /otp/send/              →   Generate login OTP               │
│    { phone_number }           →   Rate limit: 3 per 10 min/IP      │
│                               ←   "OTP sent"                       │
│                                                                     │
│  POST /login/                 →   Load User by phone               │
│    { phone, password, otp,    →   Check User.status = ACTIVE       │
│      device_id, device_name } →   Check AccountLockEvent (locked?) │
│                               →   Verify password (argon2)         │
│                               →   Verify OTP (argon2)              │
│                               →   Create LoginLog (SUCCESS)        │
│                               →   Register/update UserDevice       │
│                               →   Issue JWT (access + refresh)     │
│                               →   score_login(log.pk) ← async      │
│                               ←   { access, refresh, user }        │
│                                                                     │
│  [FAILED login attempt]                                             │
│    Bad password or OTP        →   Create LoginLog (FAILED)         │
│                               →   Increment failure counter        │
│                               →   5 failures → AccountLockEvent    │
│                               ←   HTTP 401 "Invalid credentials"   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key invariants:**
- OTP is single-use (marked VERIFIED after first successful use)
- Account auto-locks after 5 consecutive failed logins
- Every login attempt (success and failure) is recorded in `LoginLog`
- Device fingerprint is tracked in `UserDevice`
- Risk engine scores every login asynchronously (never delays response)

---

## 3. Money Transfer

```
┌─────────────────────────────────────────────────────────────────────┐
│  CUSTOMER                          BACKEND                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  POST /transfer/otp/          →   Verify user is ACTIVE + KYC      │
│    { account_id, amount }     →   Generate transfer OTP            │
│                               ←   "OTP sent"                       │
│                                                                     │
│  POST /transfer/              →   IsUserFullyActive check          │
│    { source_account_id,       →   IsKYCApproved check              │
│      dest_account_number,     →   Verify OTP                       │
│      amount, currency, otp,   →   Call post_transaction()          │
│      idempotency_key }        │                                     │
│                               │   ┌──── post_transaction() ────┐   │
│                               │   │ 1. Idempotency check        │   │
│                               │   │ 2. assert_user_active()     │   │
│                               │   │ 3. assert_kyc_approved()    │   │
│                               │   │ 4. assert_can_debit()       │   │
│                               │   │ 5. BEGIN ATOMIC             │   │
│                               │   │    SELECT FOR UPDATE x2     │   │
│                               │   │    Re-check balance         │   │
│                               │   │    Calculate fee            │   │
│                               │   │    Update balances          │   │
│                               │   │    Create entries (3)       │   │
│                               │   │    Create history snapshot  │   │
│                               │   │ 6. COMMIT                   │   │
│                               │   │ 7. on_commit: notify()      │   │
│                               │   │ 8. on_commit: score_tx()    │   │
│                               │   └─────────────────────────────┘   │
│                               ←   { reference_number, status }     │
│                                                                     │
│                               →   [POST-COMMIT]                    │
│                               →   Sender gets TRANSACTION_SENT     │
│                               →   Receiver gets TRANSACTION_RECEIVED│
│                               →   Risk engine scores transaction    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key invariants:**
- `SELECT FOR UPDATE` on both accounts prevents concurrent double-spend
- Balance is re-checked inside the lock (optimistic pre-check + pessimistic re-check)
- Idempotency key prevents duplicate processing on network retry
- Notifications and risk scoring run after commit — never delay or rollback the TX

---

## 4. QR Payment

```
┌──────────────────────────────────────────────────────────────────────────┐
│  MERCHANT                 CUSTOMER                   BACKEND             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  POST /merchant/qr/generate/                                             │
│    { amount_mode: FIXED,    →   Generate qr_token (UUID)               │
│      display_amount: 250 }  →   Hash payload (sha256)                  │
│                             →   Store QRPayment (PENDING)               │
│                             ←   { qr_token, qr_payload, expires_at }   │
│  Display QR code                                                         │
│                                                                          │
│                       Scan QR                                            │
│                       GET /payments/qr/{token}/                         │
│                                     →   Load QRPayment                  │
│                                     →   Check status = PENDING          │
│                                     →   Check not expired               │
│                                     ←   { merchant_name, amount }       │
│                                                                          │
│                       POST /payments/qr/otp/                            │
│                         { qr_token, payer_account_id }                  │
│                                     →   Generate OTP                    │
│                                     ←   "OTP sent"                      │
│                                                                          │
│                       POST /payments/qr/pay/                            │
│                         { qr_token, payer_account_id,                   │
│                           amount, otp, idempotency_key }                │
│                                     →   IsKYCApproved check             │
│                                     →   Verify OTP                      │
│                                     →   SELECT QRPayment FOR UPDATE     │
│                                     →   Assert status = PENDING         │
│                                     →   post_transaction()              │
│                                     →   QRPayment.status = PAID         │
│                                     ←   { reference_number, status }    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key invariants:**
- `SELECT FOR UPDATE` on QRPayment prevents two customers paying the same QR
- QR token is single-use (status transitions to PAID atomically)
- QR expires (configurable TTL, default 1 hour)

---

## 5. Fraud Detection

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EVENT                RISK ENGINE                RISK OFFICER            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Transaction commits                                                    │
│       ↓                                                                 │
│  on_commit fires      →   score_transaction(tx_pk)                     │
│                           └─ compute_transaction_score()               │
│                               Rule: amount ≥ SAR 5,000  → +40 pts     │
│                               Rule: amount ≥ SAR 10,000 → +75 pts     │
│                               Rule: velocity ≥ 5/hr     → +25 pts     │
│                               Rule: abnormal hour        → +15 pts     │
│                                                                         │
│                           Score < 25  → LOW  → no alert               │
│                           Score 25-49 → MEDIUM → FraudAlert (OPEN)    │
│                           Score 50-74 → HIGH   → FraudAlert (OPEN)    │
│                           Score ≥ 75  → CRITICAL → FraudAlert         │
│                                         + auto-freeze source account   │
│                                         FraudAlert (ACTIONED)         │
│                                                                         │
│  [MEDIUM / HIGH alert]                                                  │
│                                         Review queue populated         │
│                                         GET /staff/risk/alerts/        │
│                                         ← [{ id, severity, rules }]   │
│                                                                         │
│                                         POST /staff/risk/alerts/5/review/
│                                           { action: "FREEZE_ACCOUNT" } │
│                                         → FraudDecision created        │
│                                         → freeze_account() called      │
│                                         → FraudAlert.status = ACTIONED │
│                                                                         │
│  Login completes      →   score_login(log_pk)  [synchronous]          │
│                           Rule: new device        → +25 pts            │
│                           Rule: 3+ failures/30m   → +30 pts            │
│                           Rule: new country        → +20 pts            │
│                           Rule: abnormal hour      → +10 pts            │
│                           Same severity thresholds                     │
│                           Login CRITICAL: FraudAlert (no auto-freeze) │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Critical invariant:** Risk engine exceptions are swallowed — scoring failure
**never** rolls back a transaction or delays a login response.

---

## 6. KYC Enforcement

```
User attempts financial operation (Transfer / QR Pay / Bill Pay)
        │
        ↓
Layer 1: DRF view permission
  IsKYCApproved.has_permission()
  → check request.user.kyc_status == "APPROVED"
  → if NOT approved: HTTP 403
           "Your identity verification is not yet approved."
        │
        ↓ (passes Layer 1)
Layer 2: Service guard (inside post_transaction)
  _assert_kyc_approved(customer)
  → check customer.kyc_status == "APPROVED"
  → if NOT approved: raise KYCNotApprovedError
  → view catches and returns HTTP 403

Both layers must pass for the transaction to proceed.
```

---

## 7. Support Ticket Lifecycle

```
OPEN → IN_PROGRESS → RESOLVED → CLOSED
        (staff           (staff        (customer
         assigns)         resolves)     or staff)

Customer creates ticket (OPEN)
    ↓
Staff assigns to agent (IN_PROGRESS)
    ↓
Staff replies (internal notes hidden from customer)
Customer replies
    ↓
Staff resolves (RESOLVED)
    ↓
Customer or staff closes (CLOSED)
    ↓
Notification sent to customer on each staff reply
```
