# SaFe-T Backend — Complete Features, Flows & Functions Reference

> One file. Every backend feature.  
> Format per feature: **What it does → Step-by-step flow → Functions & files → ASCII diagram → DB tables touched**

---

## Table of Contents

1. [User Registration](#1-user-registration)
2. [Customer Login — 2FA](#2-customer-login--2fa)
3. [Staff Login](#3-staff-login)
4. [First-Login Setup](#4-first-login-setup)
5. [Password & PIN Reset](#5-password--pin-reset)
6. [User Unlock](#6-user-unlock)
7. [User Approval & Account Provisioning](#7-user-approval--account-provisioning)
8. [User Rejection & Blocking](#8-user-rejection--blocking)
9. [KYC Submission](#9-kyc-submission)
10. [KYC Review — Approve / Reject](#10-kyc-review)
11. [P2P Money Transfer](#11-p2p-money-transfer)
12. [QR Payment — Generate](#12-qr-payment--generate)
13. [QR Payment — Scan & Pay](#13-qr-payment--scan--pay)
14. [Bill Payment](#14-bill-payment)
15. [Teller Operations](#15-teller-operations)
16. [Transaction Reversal](#16-transaction-reversal)
17. [Transaction Archival](#17-transaction-archival)
18. [Fraud Detection — Transaction Scoring](#18-fraud-detection--transaction-scoring)
19. [Fraud Detection — Login Scoring](#19-fraud-detection--login-scoring)
20. [Risk Officer Alert Review](#20-risk-officer-alert-review)
21. [Account Freeze / Unfreeze / Block](#21-account-freeze--unfreeze--block)
22. [Beneficiary Management](#22-beneficiary-management)
23. [Support Ticket Lifecycle](#23-support-ticket-lifecycle)
24. [Notifications](#24-notifications)
25. [Reporting & Analytics](#25-reporting--analytics)
26. [OTP Internals](#26-otp-internals)
27. [post_transaction — Core Banking Engine](#27-post_transaction--core-banking-engine)
28. [Full API Endpoint Map](#28-full-api-endpoint-map)
29. [Key Design Principles](#29-key-design-principles)

---

## 1. User Registration

**What it does:** Customer self-registers via mobile app. OTP proves phone ownership before account is created.

### Flow

```
POST /api/auth/register/
  ├─ Validate phone format
  ├─ Check phone uniqueness → PhoneAlreadyExistsError if taken
  ├─ create_otp(phone, REGISTRATION)
  │     ├─ Cancel existing PENDING OTPs for same phone+type
  │     ├─ otp_plain = secrets.randbelow(1_000_000)  ← cryptographically secure
  │     ├─ otp_hash  = make_password(otp_plain)       ← Argon2, never stored plain
  │     └─ OTPRequest.create(status=PENDING, expires=5min, max_attempts=3)
  ├─ Deliver plaintext via OTP provider (Twilio / WhatsApp / dev console)
  └─ Return 200

POST /api/auth/register/complete/
  ├─ verify_otp(phone, REGISTRATION, otp_code)
  │     ├─ SELECT FOR UPDATE latest PENDING OTPRequest
  │     ├─ expired?       → OTPExpiredError
  │     ├─ max attempts?  → OTPMaxAttemptsExceededError
  │     ├─ wrong code?    → increment attempts, OTPInvalidError
  │     └─ correct?       → status=VERIFIED, verified_at=now()
  ├─ register_user(phone, full_name, password, pin)
  │     ├─ normalize_phone()  → E.164
  │     ├─ user.set_password(password)    ← Argon2
  │     ├─ user.pin_hash = make_password(pin)  ← Argon2
  │     ├─ user.status = PENDING_VERIFICATION
  │     └─ user.save()
  └─ Return 201
```

### Functions & Files

| Function | File |
|---|---|
| `create_otp()` | `apps/security/services.py` |
| `verify_otp()` | `apps/security/services.py` |
| `register_user()` | `apps/users/services.py` |
| `normalize_phone()` | `apps/users/validators.py` |
| Registration views | `apps/security/views.py` |

**DB:** `otp_requests` (INSERT/UPDATE) · `users` (INSERT)

---

## 2. Customer Login — 2FA

**What it does:** Phone + password credential check, then OTP verification. Returns JWT pair on success.

### Flow

```
POST /api/auth/login/  {phone, password, otp_code}
  │
  ├─ Find user by phone  ──not found──► 401 (enumeration-safe)
  ├─ user.is_active == False?  ──► 403 "Account locked"
  ├─ user.status == BLOCKED?   ──► 403
  ├─ first_login_completed == False? ──► 401 code=first_login_required
  │
  ├─ check_password(input, user.password)  OR  check_password(input, user.pin_hash)
  │     ──FAIL──► record_login(FAILED)
  │               check_and_auto_lock_user()  ← count failures in window
  │                 ──threshold──► lock_user() → user.is_active=False
  │               Return 401
  │
  ├─ [CUSTOMER ONLY] verify_otp(phone, LOGIN, otp_code)
  │     ── no pending OTP? ──► 401 code=otp_required (frontend sends OTP, retries)
  │
  ├─ record_login(SUCCESS, ip, device_id)
  │     └─ score_login(log.pk)  ← fraud check, synchronous, swallows errors
  ├─ register_or_update_device(user, device_uuid)
  ├─ _create_tokens(user)
  │     └─ RefreshToken.for_user() + custom claims:
  │        {role, status, full_name, phone_number, kyc_status, permissions[]}
  └─ Return 200 {access, refresh, user}
```

### ASCII Diagram

```
Customer              security/views.py            DB
   │── POST /login/ ─►│── SELECT user ────────────►│
   │                  │── check_password() ─────── (in-process)
   │                  │── verify_otp() ────────────►│ SELECT FOR UPDATE otp_requests
   │                  │── record_login(SUCCESS) ───►│ INSERT login_logs
   │                  │── score_login() ────────────► risk engine (async-safe)
   │                  │── register_or_update_device►│ UPSERT user_devices
   │                  │── _create_tokens() ───────── (in-process JWT)
   │◄── {access, refresh, user} ──────────────────────│
```

### Functions & Files

| Function | File |
|---|---|
| `login_view()` | `apps/security/views.py` |
| `verify_otp()` | `apps/security/services.py` |
| `record_login()` | `apps/security/services.py` |
| `check_and_auto_lock_user()` | `apps/security/services.py` |
| `lock_user()` | `apps/security/services.py` |
| `register_or_update_device()` | `apps/security/services.py` |
| `_create_tokens()` | `apps/security/views.py` |
| `score_login()` | `apps/risk/services.py` |
| `count_failed_logins()` | `apps/security/selectors.py` |

**DB:** `login_logs` (INSERT) · `otp_requests` (UPDATE) · `user_devices` (UPSERT) · `users` (UPDATE is_active if locked)

---

## 3. Staff Login

**What it does:** ADMIN / TELLER / RISK_OFFICER etc. authenticate with phone + password only — **no OTP required**.

### Flow

```
POST /api/auth/login/  {phone, password}
  ├─ Same guards as customer login (is_active, status, credentials)
  ├─ user.role.is_staff_role == True  →  SKIP OTP step
  ├─ record_login(SUCCESS)
  ├─ register_or_update_device()
  ├─ _create_tokens(user)  ← JWT with staff role + all permissions embedded
  └─ Return 200
```

> The `is_staff_role` field on the `Role` model (`apps/users/models.py`) controls the OTP bypass. Same `login_view()` in `apps/security/views.py` handles both paths — OTP step is conditionally skipped.

---

## 4. First-Login Setup

**What it does:** A customer registered by a teller has no real password/PIN yet. They must complete setup on first login via OTP.

### Flow

```
POST /api/auth/first-login/otp/send/
  ├─ Find user (first_login_completed=False)
  ├─ create_otp(phone, FIRST_LOGIN)
  └─ Return 200

POST /api/auth/first-login/complete/  {phone, otp_code, password, pin}
  ├─ verify_otp(phone, FIRST_LOGIN, otp_code)
  ├─ user.set_password(password)
  ├─ user.pin_hash = make_password(pin)
  ├─ user.first_login_completed = True
  ├─ user.save()
  └─ Return 200 + JWT tokens (auto-login)
```

**Functions:** `create_otp()`, `verify_otp()` — `apps/security/services.py` · views in `apps/security/views.py`

---

## 5. Password & PIN Reset

**What it does:** Customer resets a forgotten password or PIN using OTP verification. Both follow the same 3-step pattern.

> **Note:** PIN reset backend is complete (`/api/auth/pin-reset/`). The frontend only implements password reset — no PIN reset UI page exists yet.

### Password Reset Flow

```
POST /api/auth/reset-password/
  ├─ Find user by phone  (always return 200 — enumeration protection)
  ├─ create_otp(phone, PASSWORD_RESET)
  └─ Return 200

POST /api/auth/reset-password/confirm/  {phone, otp_code, new_password}
  ├─ verify_otp(phone, PASSWORD_RESET, otp_code)
  ├─ user.set_password(new_password)
  ├─ user.save()
  ├─ record_password_reset(user, RESET_PASSWORD, otp_request, ip, success=True)
  └─ Return 200
```

### PIN Reset Flow (backend only)

```
POST /api/auth/pin-reset/request/
  └─ create_otp(phone, PIN_RESET)

POST /api/auth/pin-reset/confirm/  {phone, otp_code, new_pin}
  ├─ verify_otp(phone, PIN_RESET, otp_code)
  ├─ user.pin_hash = make_password(new_pin)
  ├─ user.save()
  ├─ record_password_reset(user, RESET_PIN, ...)
  └─ Return 200
```

### Functions & Files

| Function | File |
|---|---|
| `create_otp()` | `apps/security/services.py` |
| `verify_otp()` | `apps/security/services.py` |
| `record_password_reset()` | `apps/security/services.py` |
| Password/PIN reset views | `apps/security/views.py` |

**DB:** `otp_requests` · `users` (UPDATE password/pin_hash) · `password_reset_audits` (INSERT)

---

## 6. User Unlock

**What it does:** Customer Service or Admin unlocks a user auto-locked after too many failed login attempts.

### Flow

```
POST /api/auth/users/{id}/unlock/
  ├─ HasPermission("unlock_user")
  ├─ unlock_user(user, unlocked_by=staff)
  │     ├─ Find AccountLockEvent (event_type=LOCKED, is_active=True)
  │     ├─ Set is_active=False, resolved_at=now(), unlocked_by=staff
  │     └─ If user.status in (ACTIVE, PENDING_VERIFICATION): user.is_active = True
  └─ Return 200
```

**Functions:** `unlock_user()` — `apps/security/services.py` · `HasPermission` — `apps/users/permissions.py`  
**DB:** `account_lock_events` (UPDATE) · `users` (UPDATE is_active=True)

---

## 7. User Approval & Account Provisioning

**What it does:** Teller or Admin activates a PENDING_VERIFICATION customer. Atomically creates their bank account at the same time.

### Flow

```
PATCH /api/staff/users/{id}/approve/
  ├─ HasPermission("approve_user")
  ├─ approve_user(user_id, staff_user)
  │     ├─ _assert_can_approve(): role must be TELLER or ADMIN
  │     ├─ db_transaction.atomic():
  │     │     ├─ SELECT FOR UPDATE User
  │     │     ├─ status==ACTIVE already? ──► UserAlreadyApprovedError
  │     │     ├─ user.status = ACTIVE
  │     │     ├─ user.approved_by = staff, user.approved_at = now()
  │     │     └─ create_account(user, currency="USD", created_by=staff)
  │     │           ├─ _unique_account_number()  ← 16-digit, no leading zero
  │     │           └─ Account.create(available_balance=0, status=ACTIVE)
  │     └─ Return User
  └─ Return 200
```

### ASCII Diagram

```
Staff            users/services.py         accounts/services.py       DB
  │── PATCH ────►│── atomic() ────────────────────────────────────────►│
  │              │   SELECT FOR UPDATE user ──────────────────────────►│
  │              │   UPDATE user.status=ACTIVE ────────────────────────►│
  │              │──────────────────────────►create_account() ─────────►│ INSERT accounts
  │              │── COMMIT ──────────────────────────────────────────►│
  │◄── 200 ──────│
```

### Functions & Files

| Function | File |
|---|---|
| `approve_user()` | `apps/users/services.py` |
| `_assert_can_approve()` | `apps/users/services.py` |
| `create_account()` | `apps/accounts/services.py` |
| `_unique_account_number()` | `apps/accounts/services.py` |

**DB:** `users` (UPDATE status, approved_by) · `accounts` (INSERT)

---

## 8. User Rejection & Blocking

### Reject (TELLER or ADMIN)

```
PATCH /api/staff/users/{id}/reject/
  ├─ HasPermission("reject_user")
  ├─ reject_user(user_id, staff, reason)
  │     ├─ reason must not be empty
  │     ├─ user.status = REJECTED
  │     └─ user.rejection_reason = reason
  └─ Return 200
```

### Block (ADMIN only)

```
PATCH /api/staff/users/{id}/block/
  ├─ HasPermission("block_user")
  ├─ block_user(user_id, staff, reason)
  │     ├─ _user_has_role(staff, ADMIN) ──NO──► InvalidApproverRoleError
  │     ├─ user.status = BLOCKED
  │     └─ user.blocked_reason = reason
  └─ Return 200
```

**Functions:** `reject_user()`, `block_user()` — `apps/users/services.py`

---

## 9. KYC Submission

**What it does:** Customer submits identity profile and document files. Without approved KYC, `post_transaction()` will reject all financial operations.

### Flow

```
POST /api/kyc/profile/
  └─ Create KycProfile(legal_full_name, date_of_birth, id_type, id_number, address...)

POST /api/kyc/documents/   (multipart/form-data)
  ├─ upload_kyc_document(user, document_type, file)
  │     ├─ KycDocument.create(status=PENDING)
  │     └─ If kyc_status != APPROVED:
  │           User.update(kyc_status=PENDING)
  └─ Return 201
```

### KYC Status Lifecycle

```
NOT_SUBMITTED
     │  upload_kyc_document()
     ▼
  PENDING  ◄──── re-upload after rejection
  /      \
APPROVED  REJECTED
  │
  └── post_transaction() now allowed
```

**Functions:** `upload_kyc_document()` — `apps/kyc/services.py`  
**DB:** `kyc_profiles` (INSERT) · `kyc_documents` (INSERT) · `users` (UPDATE kyc_status=PENDING)

---

## 10. KYC Review

**What it does:** Staff approves or rejects KYC. Approval unlocks full financial access for the customer.

### Approve

```
POST /api/staff/kyc/{id}/approve/
  ├─ HasPermission("review_kyc")
  ├─ approve_user_kyc(user_id, reviewed_by)
  │     ├─ Already APPROVED? ──► KycAlreadyApprovedError
  │     ├─ validate_kyc_completeness(user_id)
  │     │     ── KycProfile exists? Documents uploaded? ──INCOMPLETE──► KycIncompleteError
  │     └─ User.update(kyc_status=APPROVED)
  └─ Return 200
```

### Reject

```
POST /api/staff/kyc/{id}/reject/
  ├─ reject_user_kyc(user_id, reviewed_by, reason)
  │     ├─ kyc_status == PENDING? ──NO──► KycNotPendingError
  │     └─ User.update(kyc_status=REJECTED)
  └─ Return 200
```

### Functions & Files

| Function | File |
|---|---|
| `approve_user_kyc()` | `apps/kyc/services.py` |
| `reject_user_kyc()` | `apps/kyc/services.py` |
| `approve_kyc_document()` | `apps/kyc/services.py` |
| `reject_kyc_document()` | `apps/kyc/services.py` |
| `validate_kyc_completeness()` | `apps/kyc/validators.py` |

---

## 11. P2P Money Transfer

**What it does:** Customer sends money to another account with OTP protection. Fully atomic — either fully succeeds or fully rolls back.

### Flow

```
POST /api/payments/transfer/send-otp/
  └─ send_transfer_otp(user) → create_otp(phone, TRANSFER, purpose_ref="TRANSFER")

POST /api/payments/transfer/  {src_account, dst_account_number, amount, otp_code}
  ├─ Resolve destination account by account_number
  ├─ verify_otp(phone, TRANSFER, otp_code)  ──FAIL──► 400
  ├─ create_transfer(customer, src, dst, amount, currency, idempotency_key)
  │     ├─ src.pk != dst.pk ──SAME──► TransferSameAccountError
  │     └─ post_transaction(TRANSFER, src→dst, amount)
  └─ Return 201 {reference_number, amount}
```

### ASCII Diagram

```
Customer       payments/services.py      ledger/services.py        DB
   │── POST ──►│── verify_otp() ────────────────────────────────►│
   │           │── post_transaction() ──►│                        │
   │           │                        │── atomic() ────────────►│
   │           │                        │   SELECT FOR UPDATE accts
   │           │                        │   balance check         │
   │           │                        │   INSERT Transaction    │
   │           │                        │   BULK INSERT Entries   │
   │           │                        │   UPDATE balances       │
   │           │                        │   COMMIT ──────────────►│
   │           │                        │── on_commit:            │
   │           │                        │   score_transaction()   │
   │           │                        │   dispatch_notifications│
   │◄── 201 ───│
```

### Functions & Files

| Function | File |
|---|---|
| `send_transfer_otp()` | `apps/payments/services.py` |
| `create_transfer()` | `apps/payments/services.py` |
| `verify_otp()` | `apps/security/services.py` |
| `post_transaction()` | `apps/ledger/services.py` |

**DB:** `otp_requests` · `transactions` (INSERT) · `transaction_entries` (BULK INSERT) · `accounts` (UPDATE balances)

---

## 12. QR Payment — Generate

**What it does:** Merchant generates a QR code. Can be FIXED amount or OPEN (customer enters amount).

### Flow

```
POST /api/merchant/qr/generate/  {currency_code, amount?}
  ├─ MerchantProfile.get(user=merchant)  ──not found──► MerchantNotFoundError
  ├─ profile.status == ACTIVE? ──NO──► MerchantNotActiveError
  ├─ token = secrets.token_urlsafe(32)
  ├─ payload_hash = sha256(f"{profile.pk}:{currency}:{amount}:{token}")
  ├─ QRPayment.create(
  │       qr_token=token, amount_mode=FIXED|OPEN,
  │       expires_at=now() + TTL_HOURS)
  └─ Return 201 {qr_token, expires_at, display_amount}
```

**Functions:** `generate_qr_code()` — `apps/payments/services.py`  
**DB:** `qr_payments` (INSERT)

---

## 13. QR Payment — Scan & Pay

**What it does:** Customer scans merchant QR, verifies with OTP scoped to that specific token, money transferred atomically.

### Flow

```
GET /api/payments/qr/{token}/
  ├─ status==PAID?  ──► QRTokenAlreadyPaidError
  ├─ expired?       ──► QRTokenExpiredError
  └─ Return {merchant_name, amount, currency}

POST /api/payments/qr/{token}/send-otp/
  └─ create_otp(phone, QR_PAYMENT, purpose_ref=qr_token)
        ← OTP is scoped to THIS specific QR token

POST /api/payments/qr/{token}/pay/  {otp_code, amount?}
  ├─ process_qr_payment(payer, payer_account, qr_token, otp_code, amount)
  │     ├─ Re-check status and expiry
  │     ├─ pay_amount = FIXED: display_amount  |  OPEN: caller amount
  │     ├─ verify_otp(phone, QR_PAYMENT, otp_code, purpose_ref=qr_token)
  │     ├─ UPDATE qr_payment.scanned_at = now()
  │     ├─ post_transaction(QR_PAYMENT, payer→merchant_account, pay_amount)
  │     └─ UPDATE qr_payment: status=PAID, transaction=tx
  └─ Return 201
```

**Functions:** `send_qr_payment_otp()`, `process_qr_payment()` — `apps/payments/services.py`  
**DB:** `qr_payments` (UPDATE PAID) · `transactions` · `transaction_entries` · `accounts`

---

## 14. Bill Payment

**What it does:** Customer pays a utility/service bill. Amount is fetched first, then paid with OTP.

### Flow

```
GET /api/payments/bills/{provider_code}/fetch/?service_number=X
  ├─ fetch_bill_info(provider_code, service_number)
  │     ├─ BillProvider.get(code=provider_code) ──not found──► BillProviderNotFoundError
  │     └─ Return {provider_name, amount, bill_reference}

POST /api/payments/bills/send-otp/
  └─ create_otp(phone, BILL_PAYMENT, purpose_ref=f"{provider_code}:{service_number}")

POST /api/payments/bills/pay/  {provider_code, service_number, amount, otp_code}
  ├─ process_bill_payment(customer, payer_account, provider_code, ...)
  │     ├─ BillProvider.get(code=..., is_active=True)
  │     ├─ verify_otp(phone, BILL_PAYMENT, otp_code, purpose_ref=provider:service)
  │     ├─ post_transaction(BILL_PAYMENT, payer→provider.provider_account, amount)
  │     └─ BillPayment.create(transaction=tx, paid_at=now())
  └─ Return 201
```

### Functions & Files

| Function | File |
|---|---|
| `fetch_bill_info()` | `apps/payments/services.py` |
| `send_bill_payment_otp()` | `apps/payments/services.py` |
| `process_bill_payment()` | `apps/payments/services.py` |
| `verify_otp()` | `apps/security/services.py` |
| `post_transaction()` | `apps/ledger/services.py` |

**DB:** `bill_providers` (SELECT) · `otp_requests` · `transactions` · `transaction_entries` · `bill_payments` (INSERT) · `accounts`

---

## 15. Teller Operations

### Teller Deposit

```
POST /api/staff/teller/deposit/  {account_number, amount}
  ├─ HasPermission("staff_deposit")
  ├─ cash_vault = Account.get(settings.LEDGER_CASH_ACCOUNT_NUMBER)
  ├─ post_transaction(DEPOSIT,
  │       source=cash_vault,       ← vault debited
  │       destination=customer,    ← customer credited
  │       channel=TELLER)
  └─ Return 201
```

### Teller Withdrawal

```
POST /api/staff/teller/withdraw/  {account_number, amount}
  ├─ HasPermission("staff_withdraw")
  ├─ post_transaction(WITHDRAWAL,
  │       source=customer,         ← customer debited
  │       destination=cash_vault,  ← vault credited
  │       channel=TELLER)
  └─ Return 201
```

### Teller Register Customer

```
POST /api/staff/teller/register-customer/  {phone, full_name}
  ├─ HasPermission("staff_register_customer")
  ├─ register_user(phone, full_name, password=TEMP, pin=TEMP)
  │     └─ status=PENDING_VERIFICATION, first_login_completed=False
  └─ Return 201  ← customer must later call /first-login/complete/
```

**Functions:** `post_transaction()` — `apps/ledger/services.py` · `register_user()` — `apps/users/services.py`  
Views in `apps/users/teller_views.py`

---

## 16. Transaction Reversal

**What it does:** Staff reverses a COMPLETED transaction. The original is never deleted — a new offsetting transaction is created with swapped entries.

### Flow

```
POST /api/staff/ledger/reverse/  {reference_number, reason}
  ├─ HasPermission("reverse_transaction")
  ├─ reverse_transaction(reference_number, reason, initiated_by=staff)
  │     ├─ Fetch original tx + entries  ──not found──► TransactionNotFoundError
  │     ├─ reversed_at not None?        ──► TransactionAlreadyReversedError
  │     ├─ status != COMPLETED?         ──► TransactionNotReversibleError
  │     │
  │     ├─ db_transaction.atomic():
  │     │     ├─ SELECT FOR UPDATE all involved accounts (sorted PKs)
  │     │     ├─ _reference_number(tx_type)  ← new reversal ref
  │     │     ├─ Transaction.create(parent_transaction=original, status=COMPLETED)
  │     │     ├─ Build swapped entries (see table below)
  │     │     ├─ TransactionEntry.bulk_create(reversed_entries)
  │     │     ├─ _assert_entries_balanced(reversal)
  │     │     ├─ Reverse balance changes
  │     │     └─ UPDATE original: status=REVERSED, reversed_at=now()
  │     └─ Return reversal Transaction
  └─ Return 201
```

### Entry Type Swap

```
Original Entry    Reversal Entry
──────────────    ──────────────
DEBIT          →  CREDIT
CREDIT         →  DEBIT
FEE            →  CREDIT  (fee returned to customer)
```

### Functions & Files

| Function | File |
|---|---|
| `reverse_transaction()` | `apps/ledger/services.py` |
| `_assert_entries_balanced()` | `apps/ledger/services.py` |
| `_reference_number()` | `apps/ledger/services.py` |

**DB:** `transactions` (INSERT reversal + UPDATE original REVERSED) · `transaction_entries` (BULK INSERT) · `accounts` (UPDATE balances reversed)

---

## 17. Transaction Archival

**What it does:** Creates an immutable JSON snapshot of a completed transaction for compliance and audit, even if live rows change later.

### Flow

```
archive_transaction(transaction)   ← apps/ledger/services.py
  ├─ Already archived? → return existing  (idempotent)
  ├─ Build entries_snapshot: [{entry_type, amount, sequence_no, account_id}, ...]
  └─ TransactionHistory.create(
          reference_number=tx.reference_number,
          payload_json={description, channel, customer_id, entries})
```

**DB:** `transaction_history` (INSERT — immutable, never updated)

---

## 18. Fraud Detection — Transaction Scoring

**What it does:** After every committed transaction, a hybrid ML + rules engine scores it. High scores create `FraudAlert` records. Critical scores auto-freeze the account.

### Flow

```
[post_transaction() COMMIT] → on_commit hook fires
  └─ score_transaction(tx_pk)   ← apps/risk/services.py
        │
        ├─ Fetch Transaction + source account (first DEBIT entry)
        │
        ├─ RULE ENGINE  →  compute_transaction_score(tx_pk)  (apps/risk/rules.py)
        │     ├─ _rule_amount(amount)
        │     │     ≥ AMOUNT_CRITICAL_THRESHOLD? → +score CRITICAL
        │     │     ≥ AMOUNT_HIGH_THRESHOLD?     → +score HIGH
        │     ├─ _rule_velocity(source_account_pk, exclude_tx_pk)
        │     │     count DEBIT entries last VELOCITY_WINDOW_HOURS
        │     │     ≥ VELOCITY_COUNT_HIGH?   → +score
        │     │     ≥ VELOCITY_COUNT_MEDIUM? → +score
        │     └─ _rule_abnormal_hour_tx(occurred_at)
        │           abnormal hour? → +score
        │
        ├─ ML ENGINE  →  extract_transaction_features(tx) + predict_transaction_fraud(features)
        │     └─ Load fraud_model.pkl (scikit-learn Random Forest)
        │        Return ml_probability  (0.0 – 1.0)
        │
        ├─ combined_score = (rule_score × 0.4) + (ml_probability × 100 × 0.6)
        │
        ├─ Severity:
        │     ≥ CRITICAL_THRESHOLD → CRITICAL
        │     ≥ HIGH_THRESHOLD     → HIGH
        │     ≥ MEDIUM_THRESHOLD   → MEDIUM
        │     else                 → LOW  (no alert created)
        │
        ├─ If severity ≥ MEDIUM:
        │     FraudAlert.create(alert_type=SUSPICIOUS_TRANSACTION, ...)
        │
        └─ If severity == CRITICAL AND rule_score ≥ 50:
              freeze_account(source_account, reason="AUTO_FRAUD_FREEZE")
```

### ASCII Diagram

```
post_transaction() COMMIT
        │
        └─ on_commit ──────────────► score_transaction(tx_pk)
                                              │
                          ┌───────────────────┴──────────────────────┐
                          │  RULE ENGINE            ML ENGINE         │
                          │  _rule_amount()         feature_builder   │
                          │  _rule_velocity()       predictor.py      │
                          │  _rule_abnormal_hour()  RandomForest.pkl  │
                          │  → rule_score (int)     → ml_probability  │
                          └───────────────────┬──────────────────────┘
                                              │
                                      combined_score
                                              │
                          ┌───────────────────┴──────────────────────┐
                          │           Severity Decision               │
                          │  CRITICAL → FraudAlert + auto-freeze     │
                          │  HIGH/MED → FraudAlert (OPEN)            │
                          │  LOW      → no action                    │
                          └──────────────────────────────────────────┘
```

### Functions & Files

| Function | File |
|---|---|
| `score_transaction()` | `apps/risk/services.py` |
| `compute_transaction_score()` | `apps/risk/rules.py` |
| `_rule_amount()` | `apps/risk/rules.py` |
| `_rule_velocity()` | `apps/risk/rules.py` |
| `_rule_abnormal_hour_tx()` | `apps/risk/rules.py` |
| `extract_transaction_features()` | `apps/risk/ml/feature_builder.py` |
| `predict_transaction_fraud()` | `apps/risk/ml/predictor.py` |
| `freeze_account()` | `apps/accounts/services.py` |

**DB:** `fraud_alerts` (INSERT if ≥ MEDIUM) · `account_restrictions` (INSERT if auto-freeze)

---

## 19. Fraud Detection — Login Scoring

**What it does:** After every login attempt, rules detect account takeover signals (too many failures, new device, new country, abnormal hour).

### Flow

```
record_login() → score_login(login_log.pk)   ← synchronous, errors swallowed
  └─ compute_login_score(login_log_pk)  (apps/risk/rules.py)
        ├─ _rule_recent_failures(phone, exclude_pk)
        │     count FAILED logins in FAILED_LOGIN_WINDOW_MIN
        │     ≥ HIGH_COUNT → +score  |  ≥ LOW_COUNT → +score
        ├─ _rule_new_device(user_pk, device_id)
        │     UserDevice with this uuid exists? NO → +score
        ├─ _rule_new_country(user_pk, country)
        │     never logged in from this country? → +score
        └─ _rule_abnormal_hour_login(attempted_at)
              late night hour? → +score

  + ML ENGINE → predict_login_fraud(features)
  → combined_score → FraudAlert(SUSPICIOUS_LOGIN) if ≥ MEDIUM
```

### Functions & Files

| Function | File |
|---|---|
| `score_login()` | `apps/risk/services.py` |
| `compute_login_score()` | `apps/risk/rules.py` |
| `_rule_recent_failures()` | `apps/risk/rules.py` |
| `_rule_new_device()` | `apps/risk/rules.py` |
| `_rule_new_country()` | `apps/risk/rules.py` |
| `_rule_abnormal_hour_login()` | `apps/risk/rules.py` |

---

## 20. Risk Officer Alert Review

**What it does:** Risk Officer reviews open `FraudAlert` records and takes action — freeze, block, warn, escalate, or dismiss.

### Flow

```
GET  /api/staff/risk/alerts/           ← list, ?status=OPEN&severity=CRITICAL
GET  /api/staff/risk/alerts/{id}/      ← detail + existing decision

POST /api/staff/risk/alerts/{id}/review/  {action, notes}
  ├─ HasPermission("review_fraud_alert")
  ├─ action ∈ {FREEZE_ACCOUNT, BLOCK_ACCOUNT, DISMISS, WARN, ESCALATE}
  ├─ review_alert(alert_id, officer, action, notes)
  │     ├─ alert not found?       → AlertNotFoundError
  │     ├─ alert.status != OPEN?  → AlertAlreadyReviewedError
  │     ├─ FraudDecision.create(alert, officer, action, notes)
  │     ├─ Execute physical action:
  │     │     FREEZE_ACCOUNT → freeze_account(alert.account)
  │     │     BLOCK_ACCOUNT  → block_account(alert.account)
  │     │     WARN / ESCALATE / DISMISS → no account action
  │     ├─ alert.status = REVIEWED, reviewed_by = officer
  │     └─ alert.reviewed_at = now()
  └─ Return 200

POST /api/staff/risk/alerts/{id}/dismiss/   ← shortcut (no body needed)
  └─ dismiss_alert(alert_id, officer)
```

### Alert Lifecycle

```
Transaction / Login event
        │
   score_*() fires
        │
   ┌────▼────┐
   │  OPEN   │
   └────┬────┘
        │  Risk Officer reviews
   ┌────▼────────────────────────────────────────────┐
   │ FREEZE_ACCOUNT │ BLOCK_ACCOUNT │ WARN │ DISMISS │
   └────┬────────────────────────────────────────────┘
        │
   ┌────▼────┐
   │REVIEWED │
   └─────────┘
```

### Functions & Files

| Function | File |
|---|---|
| `review_alert()` | `apps/risk/services.py` |
| `dismiss_alert()` | `apps/risk/services.py` |
| `get_alerts()` | `apps/risk/selectors.py` |
| `get_alert_by_id()` | `apps/risk/selectors.py` |
| `freeze_account()` | `apps/accounts/services.py` |
| `block_account()` | `apps/accounts/services.py` |
| `alert_list()` | `apps/risk/views.py` |
| `alert_review()` | `apps/risk/views.py` |
| `alert_dismiss()` | `apps/risk/views.py` |

**DB:** `fraud_decisions` (INSERT) · `fraud_alerts` (UPDATE REVIEWED) · `account_restrictions` · `accounts`

---

## 21. Account Freeze / Unfreeze / Block

**What it does:** Staff restricts or lifts restrictions on a customer account. Every debit operation checks account status before proceeding.

### Freeze

```
PATCH /api/staff/accounts/{id}/freeze/
  ├─ HasPermission("freeze_account")
  ├─ freeze_account(account, reason, applied_by=staff)
  │     ├─ atomic(): deactivate existing FREEZE restriction
  │     ├─ AccountRestriction.create(restriction_type=FREEZE, is_active=True)
  │     └─ Account.update(status=FROZEN)
  └─ Return 200
```

### Unfreeze

```
PATCH /api/staff/accounts/{id}/unfreeze/
  ├─ unfreeze_account(account, resolved_by=staff)
  │     ├─ AccountRestriction.filter(FREEZE, is_active=True).update(is_active=False)
  │     └─ Account.update(status=ACTIVE)
  └─ Return 200
```

### Block

```
PATCH /api/staff/accounts/{id}/block/
  ├─ block_account(account, reason, applied_by=staff)
  │     ├─ AccountRestriction.create(restriction_type=BLOCK)
  │     └─ Account.update(status=BLOCKED)
  └─ Return 200
```

### Account Status Gate (checked before every debit)

```
assert_account_can_debit(account)   ← apps/accounts/selectors.py
  ├─ status == FROZEN  → AccountFrozenError
  ├─ status == BLOCKED → AccountBlockedError
  └─ status == CLOSED  → AccountClosedError
```

**Functions:** `freeze_account()`, `unfreeze_account()`, `block_account()` — `apps/accounts/services.py`  
`assert_account_can_debit()` — `apps/accounts/selectors.py`  
**DB:** `account_restrictions` (INSERT/UPDATE) · `accounts` (UPDATE status)

---

## 22. Beneficiary Management

**What it does:** Customer saves frequently-used destination accounts with a nickname for quick transfers.

### Add

```
POST /api/accounts/beneficiaries/  {destination_account_id, nickname}
  ├─ Account.get(pk=destination_id)  ──not found──► AccountNotFoundError
  ├─ Beneficiary.get_or_create(owner=user, destination_account=dest)
  │     already exists? → BeneficiaryAlreadyExistsError
  └─ Return 201
```

### Remove

```
DELETE /api/accounts/beneficiaries/{id}/
  ├─ Beneficiary.get(pk=id, owner=user)
  └─ beneficiary.delete()
```

**Functions:** `add_beneficiary()`, `remove_beneficiary()` — `apps/accounts/services.py`  
**DB:** `beneficiaries` (INSERT / DELETE)

---

## 23. Support Ticket Lifecycle

**What it does:** Customers raise tickets. Staff reply (with optional internal-only notes) and resolve them.

### Create Ticket

```
POST /api/support/tickets/  {subject, category, body}
  ├─ create_ticket(user, subject, category, body)
  │     ├─ SupportTicket.create(status=OPEN)
  │     ├─ SupportTicketMessage.create(sender=user, body=body, is_internal=False)
  │     └─ dispatch_notification(user, TICKET_OPENED)
  └─ Return 201
```

### Staff Reply

```
POST /api/staff/support/tickets/{id}/reply/  {body, is_internal?}
  ├─ HasPermission("manage_support_tickets")
  ├─ reply_to_ticket(ticket_id, sender=staff, body, is_internal)
  │     ├─ ticket.status == CLOSED? → TicketClosedError
  │     ├─ SupportTicketMessage.create(is_internal=True|False)
  │     ├─ If OPEN: ticket.status = IN_PROGRESS
  │     └─ dispatch_notification(customer, TICKET_REPLIED)  ← if not internal
  └─ Return 201
```

### Resolve

```
PATCH /api/staff/support/tickets/{id}/resolve/
  ├─ resolve_ticket(ticket_id, resolved_by=staff)
  │     ├─ ticket.status = RESOLVED, resolved_at = now()
  │     └─ dispatch_notification(customer, TICKET_RESOLVED)
  └─ Return 200
```

### Lifecycle

```
OPEN ──► IN_PROGRESS ──► RESOLVED ──► CLOSED
```

**Functions:** `create_ticket()`, `reply_to_ticket()`, `resolve_ticket()`, `close_ticket()` — `apps/support/services.py`  
**DB:** `support_tickets` · `support_ticket_messages` · `notifications`

---

## 24. Notifications

**What it does:** In-app notifications created automatically after transactions, KYC changes, and ticket events.

### Post-Transaction (on_commit hook)

```
dispatch_post_transaction_notifications(tx_pk)
  ├─ Find DEBIT entry  → sender
  ├─ Find CREDIT entry → receiver
  ├─ dispatch_notification(sender,   TRANSACTION_SENT,     "Money Sent: {amount}")
  └─ dispatch_notification(receiver, TRANSACTION_RECEIVED, "Money Received: {amount}")
```

### Notification Types

| Type | Triggered By |
|---|---|
| `TRANSACTION_SENT` | `post_transaction()` on_commit |
| `TRANSACTION_RECEIVED` | `post_transaction()` on_commit |
| `TICKET_OPENED` | `create_ticket()` |
| `TICKET_REPLIED` | `reply_to_ticket()` |
| `TICKET_RESOLVED` | `resolve_ticket()` |
| `KYC_APPROVED` | `approve_user_kyc()` |
| `KYC_REJECTED` | `reject_user_kyc()` |

### Mark Read

```
POST /api/support/notifications/{id}/read/
  └─ mark_notification_read(notification_id, user)

POST /api/support/notifications/read-all/
  └─ mark_all_notifications_read(user)
```

**Functions:** `dispatch_notification()`, `mark_notification_read()`, `mark_all_notifications_read()` — `apps/support/services.py`  
**DB:** `notifications` (INSERT / UPDATE is_read)

---

## 25. Reporting & Analytics

**What it does:** Staff dashboards over transaction volumes, user stats, fraud metrics. The `reporting` app has **no models** — it is a pure query layer over other apps' tables.

### Flow

```
GET /api/staff/reports/summary/
  ├─ HasPermission("view_all_transactions")
  ├─ get_transaction_volume_by_type(date_from, date_to)
  │     Transaction.filter(...).values("transaction_type").annotate(count, total)
  ├─ get_daily_transaction_totals(date_from, date_to)
  ├─ get_user_registration_stats(date_from, date_to)
  ├─ get_fraud_alert_stats()
  │     FraudAlert.values("severity").annotate(count)
  ├─ get_account_balance_summary()
  └─ get_kyc_status_breakdown()
```

**Files:** All selectors in `apps/reporting/selectors.py` · views in `apps/reporting/views.py`

---

## 26. OTP Internals

### OTP Types & Scopes

| Type | Used For | purpose_ref |
|---|---|---|
| `REGISTRATION` | Self-registration | empty |
| `LOGIN` | Customer 2FA login | empty |
| `FIRST_LOGIN` | Teller-registered customer setup | empty |
| `PASSWORD_RESET` | Forgot password | empty |
| `PIN_RESET` | Forgot PIN | empty |
| `TRANSFER` | P2P transfer | `"TRANSFER"` |
| `QR_PAYMENT` | QR payment | `qr_token` value |
| `BILL_PAYMENT` | Bill payment | `"provider_code:service_number"` |

### Generation (apps/security/services.py)

```
create_otp(phone, request_type, purpose_ref, ip, device_id, user)
  ├─ Cancel all PENDING for same (phone, type, purpose_ref)
  ├─ otp_plain = str(secrets.randbelow(1_000_000)).zfill(6)   ← CSPRNG 6-digit
  ├─ If DEBUG + ENABLE_DEV_OTP: print(otp_plain) to console
  ├─ otp_hash = make_password(otp_plain)   ← Argon2 hash, plaintext discarded
  ├─ OTPRequest.create(status=PENDING, expires=+5min, max_attempts=3)
  └─ Return (OTPRequest, otp_plain)
        └─ plaintext passed ONCE to provider, NEVER stored
```

### Verification — Race-Condition Safe (apps/security/services.py)

```
verify_otp(phone, request_type, otp_plain, purpose_ref)
  ├─ db_transaction.atomic():
  │     ├─ SELECT FOR UPDATE latest PENDING OTPRequest
  │     │     ← Row lock prevents two concurrent requests both passing
  │     ├─ NOT FOUND      → OTPNotFoundError
  │     ├─ expired        → status=EXPIRED,  raise OTPExpiredError
  │     ├─ max attempts   → status=FAILED,   raise OTPMaxAttemptsExceededError
  │     ├─ wrong code     → attempts += 1,   raise OTPInvalidError
  │     └─ correct        → status=VERIFIED, verified_at=now()
  └─ Raise saved exception OUTSIDE atomic()
        ← Guarantees attempts counter is committed even when error is raised
```

### OTP Provider Factory (apps/security/otp/factory.py)

```
get_otp_service()
  ├─ OTP_PROVIDER == "dev"          → DevOTPService       (console only, no SMS)
  ├─ OTP_PROVIDER == "twilio"       → TwilioOTPService    (SMS via Twilio Verify)
  ├─ OTP_PROVIDER == "whatsapp"     → WhatsAppOTPService  (WhatsApp API)
  └─ OTP_PROVIDER == "wa_otp_mini"  → WaOtpMiniService    (local WhatsApp bot)
```

---

## 27. post_transaction — Core Banking Engine

**What it does:** The **single authoritative function** for all money movement. Every payment type calls this. You must never modify account balances directly — only through this function.

### Complete Internal Flow

```
post_transaction(transaction_type, currency_code, amount,
                 source_account, destination_account,
                 description, channel, initiated_by, customer,
                 idempotency_key, requires_otp, otp_verified_at, metadata)
  │
  ├─ [G1] amount > 0                              ──NO──► ValueError
  ├─ [G2] source.pk != destination.pk             ──SAME──► ValueError
  ├─ [G3] _assert_user_active(customer)
  │         customer.status == PENDING_VERIFICATION ──► UserNotActiveError
  ├─ [G4] _assert_kyc_approved(customer)
  │         customer.kyc_status != APPROVED ──► KYCNotApprovedError
  ├─ [G5] assert_account_can_debit(source) [PRE-LOCK]
  │         FROZEN / BLOCKED / CLOSED ──► matching Error
  │
  ├─ [IDEMPOTENCY] if idempotency_key:
  │     existing = Transaction.filter(idempotency_key).first()
  │     COMPLETED   → return existing safely  (retry-safe)
  │     PROCESSING  → DuplicateTransactionError
  │
  ├─ db_transaction.atomic():
  │     ├─ sorted_pks = sorted([src.pk, dst.pk])
  │     │     SELECT FOR UPDATE accounts in ascending PK order
  │     │     ← Deadlock prevention: always lock in same order
  │     │
  │     ├─ [G5 again] assert_account_can_debit(locked_source) [POST-LOCK]
  │     │     ← TOCTOU: status may have changed between pre-lock check and now
  │     │
  │     ├─ calculate_fee(tx_type, currency, amount)
  │     │     ├─ FeeRule.filter(type + currency + amount range + active date range)
  │     │     ├─ fee = fixed_fee + (amount × percentage_fee)
  │     │     ├─ fee = clamp(min_fee ≤ fee ≤ max_fee)
  │     │     └─ Return (fee_amount, fee_pool_account)
  │     │
  │     ├─ total_debit = amount + fee_amount
  │     ├─ available_balance < total_debit → InsufficientFundsError
  │     │
  │     ├─ If fee > 0: SELECT FOR UPDATE fee_pool account
  │     │
  │     ├─ Transaction.create(status=PROCESSING, reference=_reference_number())
  │     │     prefix: TRF / DEP / WTH / QRP / BLP depending on type
  │     │
  │     ├─ Build double-entry records:
  │     │     seq1: DEBIT  source       amount
  │     │     seq2: CREDIT destination  amount
  │     │     seq3: FEE    source       fee_amount  (only if fee > 0)
  │     │     seq4: CREDIT fee_pool     fee_amount  (only if fee > 0)
  │     │
  │     ├─ TransactionEntry.bulk_create(entries)
  │     │
  │     ├─ _assert_entries_balanced(tx)
  │     │     sum(DEBIT + FEE amounts) == sum(CREDIT amounts)
  │     │     ──UNBALANCED──► TransactionBalanceError → ROLLBACK entire atomic block
  │     │
  │     ├─ Account.update(source):      available -= total_debit, ledger -= total_debit
  │     ├─ Account.update(destination): available += amount,      ledger += amount
  │     ├─ Account.update(fee_pool):    available += fee_amount,  ledger += fee_amount
  │     │
  │     ├─ Transaction.update(status=COMPLETED, completed_at=now())
  │     └─ COMMIT
  │
  ├─ on_commit(_post_commit):    ← fires AFTER DB commit, never blocks the caller
  │     ├─ dispatch_post_transaction_notifications(tx_pk)   (try/except: swallowed)
  │     └─ score_transaction(tx_pk)                         (try/except: swallowed)
  │
  └─ Return completed Transaction
```

### Who Calls post_transaction

```
┌─────────────────────────────────────────────────────────────────┐
│                      post_transaction()                         │
│                   apps/ledger/services.py                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ called by
   ┌───────────────────────┼────────────────────────────────────┐
   │                       │                                    │
create_transfer()  process_qr_payment()   process_bill_payment()
payments/services  payments/services      payments/services
   │                       │                                    │
teller deposit     teller withdrawal              staff reversal
teller_views.py    teller_views.py                ledger/views.py
```

### Double-Entry Example: $100 Transfer + $2 Fee

```
Entry  Type    Account        Amount
─────  ──────  ─────────────  ──────
  1    DEBIT   Alice          100.00  ← Alice's balance falls
  2    CREDIT  Bob            100.00  ← Bob's balance rises
  3    FEE     Alice            2.00  ← Fee deducted from Alice
  4    CREDIT  Fee Pool          2.00  ← Bank collects the fee

Debit total  = 100.00 + 2.00 = 102.00
Credit total = 100.00 + 2.00 = 102.00  ✓  BALANCED

Alice net: -102.00  |  Bob net: +100.00  |  Fee Pool: +2.00
```

### Functions & Files

| Function | File |
|---|---|
| `post_transaction()` | `apps/ledger/services.py` |
| `_assert_user_active()` | `apps/ledger/services.py` |
| `_assert_kyc_approved()` | `apps/ledger/services.py` |
| `_assert_entries_balanced()` | `apps/ledger/services.py` |
| `_reference_number()` | `apps/ledger/services.py` |
| `calculate_fee()` | `apps/ledger/services.py` |
| `assert_account_can_debit()` | `apps/accounts/selectors.py` |
| `dispatch_post_transaction_notifications()` | `apps/support/services.py` |
| `score_transaction()` | `apps/risk/services.py` |

**DB:** `transactions` (INSERT → UPDATE COMPLETED) · `transaction_entries` (BULK INSERT) · `accounts` (UPDATE ×3) · `fee_rules` (SELECT)

---

## 28. Full API Endpoint Map

| Endpoint | Method | App | Permission Required |
|---|---|---|---|
| `/api/auth/register/` | POST | security | Public |
| `/api/auth/register/complete/` | POST | security | Public |
| `/api/auth/otp/send/` | POST | security | Public |
| `/api/auth/login/` | POST | security | Public |
| `/api/auth/token/refresh/` | POST | security | Public |
| `/api/auth/reset-password/` | POST | security | Public |
| `/api/auth/reset-password/confirm/` | POST | security | Public |
| `/api/auth/pin-reset/request/` | POST | security | Authenticated |
| `/api/auth/pin-reset/confirm/` | POST | security | Authenticated |
| `/api/auth/first-login/otp/send/` | POST | security | Public |
| `/api/auth/first-login/complete/` | POST | security | Public |
| `/api/auth/users/{id}/unlock/` | POST | security | `unlock_user` |
| `/api/accounts/` | GET | accounts | `IsActiveUser` |
| `/api/accounts/beneficiaries/` | GET/POST | accounts | `IsActiveUser` |
| `/api/accounts/beneficiaries/{id}/` | DELETE | accounts | `IsActiveUser` |
| `/api/ledger/transactions/` | GET | ledger | `IsActiveUser` |
| `/api/ledger/transactions/{ref}/` | GET | ledger | `IsActiveUser` |
| `/api/payments/transfer/send-otp/` | POST | payments | `IsKYCApproved` |
| `/api/payments/transfer/` | POST | payments | `IsKYCApproved` |
| `/api/payments/qr/{token}/` | GET | payments | Authenticated |
| `/api/payments/qr/{token}/send-otp/` | POST | payments | Authenticated |
| `/api/payments/qr/{token}/pay/` | POST | payments | `IsKYCApproved` |
| `/api/payments/bills/{code}/fetch/` | GET | payments | Authenticated |
| `/api/payments/bills/send-otp/` | POST | payments | Authenticated |
| `/api/payments/bills/pay/` | POST | payments | `IsKYCApproved` |
| `/api/merchant/qr/generate/` | POST | payments | Merchant role |
| `/api/kyc/profile/` | GET/POST | kyc | `IsActiveUser` |
| `/api/kyc/documents/` | POST | kyc | `IsActiveUser` |
| `/api/support/tickets/` | GET/POST | support | `IsActiveUser` |
| `/api/support/tickets/{id}/` | GET | support | `IsActiveUser` |
| `/api/support/notifications/` | GET | support | Authenticated |
| `/api/support/notifications/{id}/read/` | POST | support | Authenticated |
| `/api/staff/users/` | GET | users | `IsStaffUser` |
| `/api/staff/users/{id}/approve/` | PATCH | users | `approve_user` |
| `/api/staff/users/{id}/reject/` | PATCH | users | `reject_user` |
| `/api/staff/users/{id}/block/` | PATCH | users | `block_user` |
| `/api/staff/accounts/{id}/freeze/` | PATCH | accounts | `freeze_account` |
| `/api/staff/accounts/{id}/unfreeze/` | PATCH | accounts | `unfreeze_account` |
| `/api/staff/accounts/{id}/block/` | PATCH | accounts | `block_account` |
| `/api/staff/teller/deposit/` | POST | users | `staff_deposit` |
| `/api/staff/teller/withdraw/` | POST | users | `staff_withdraw` |
| `/api/staff/teller/register-customer/` | POST | users | `staff_register_customer` |
| `/api/staff/kyc/{id}/approve/` | POST | kyc | `review_kyc` |
| `/api/staff/kyc/{id}/reject/` | POST | kyc | `review_kyc` |
| `/api/staff/ledger/reverse/` | POST | ledger | `reverse_transaction` |
| `/api/staff/risk/alerts/` | GET | risk | `review_fraud_alert` |
| `/api/staff/risk/alerts/{id}/` | GET | risk | `review_fraud_alert` |
| `/api/staff/risk/alerts/{id}/review/` | POST | risk | `review_fraud_alert` |
| `/api/staff/risk/alerts/{id}/dismiss/` | POST | risk | `review_fraud_alert` |
| `/api/staff/support/tickets/{id}/reply/` | POST | support | `manage_support_tickets` |
| `/api/staff/support/tickets/{id}/resolve/` | PATCH | support | `manage_support_tickets` |
| `/api/staff/reports/summary/` | GET | reporting | `view_all_transactions` |

---

## 29. Key Design Principles

| Principle | Where Applied | Why |
|---|---|---|
| **Atomic transactions** | `post_transaction()`, `approve_user()`, `freeze_account()` | All-or-nothing — partial writes never happen |
| **Deadlock prevention** | `post_transaction()` locks accounts in ascending PK order | Two concurrent transfers between same accounts always lock in same order |
| **TOCTOU protection** | Balance checked pre-lock AND again post-lock inside `atomic()` | Account status could change between the two checks |
| **Double-entry invariant** | `_assert_entries_balanced()` before COMPLETED | Debits must always equal credits — accounting rule |
| **Idempotency** | `idempotency_key` on transactions; `archive_transaction()` | Safe retries — duplicate requests return the same result |
| **OTP race-condition safety** | `verify_otp()` uses `SELECT FOR UPDATE` | Prevents two requests both verifying the same OTP |
| **Enumeration protection** | Login and password reset return identical messages for missing users | Attacker cannot discover which phone numbers are registered |
| **Non-blocking post-commit** | Notifications and fraud scoring via `on_commit()` | A notification failure must never undo a committed transaction |
| **Argon2 everywhere** | Passwords, PINs, and OTP codes | Memory-hard hashing — resistant to GPU brute-force |
| **Role-based access** | `HasPermission`, `IsAdminRole`, `IsStaffUser` on every write endpoint | Granular control — each staff role can only do what it is permitted |
| **Service layer only** | Views never contain business logic | All logic in `services.py`; views only validate input and call services |
| **Deferred imports** | Risk and notification imports inside `on_commit` callbacks | Avoids circular imports between `ledger`, `risk`, and `support` apps |
