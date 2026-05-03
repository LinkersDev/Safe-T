# SafeT Backend — API Overview

Base URL: `http://localhost:8000`

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## Auth (`/api/auth/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register/` | No | Start registration — send OTP to phone |
| POST | `/api/auth/register/verify-otp/` | No | Verify registration OTP |
| POST | `/api/auth/register/complete/` | No | Set password, full name after OTP verified |
| POST | `/api/auth/otp/send/` | No | Send login OTP |
| POST | `/api/auth/login/` | No | Login with phone + password + OTP → JWT tokens |
| POST | `/api/auth/token/refresh/` | No | Refresh access token |
| POST | `/api/auth/logout/` | Yes | Invalidate refresh token |
| POST | `/api/auth/password/change/` | Yes | Change password |
| POST | `/api/auth/pin/set/` | Yes | Set / change transaction PIN |

### POST `/api/auth/register/`
```json
Request:  { "phone_number": "+966500000001" }
Response: { "detail": "OTP sent to +966500000001" }
```

### POST `/api/auth/register/verify-otp/`
```json
Request:  { "phone_number": "+966500000001", "otp": "123456" }
Response: { "detail": "OTP verified. Proceed to complete registration." }
```

### POST `/api/auth/register/complete/`
```json
Request:  { "phone_number": "+966500000001", "password": "SecurePass1!", "full_name": "Ali Hassan" }
Response: { "detail": "Registration complete. Awaiting staff approval." }
```

### POST `/api/auth/otp/send/`
```json
Request:  { "phone_number": "+966500000001" }
Response: { "detail": "OTP sent." }
```

### POST `/api/auth/login/`
```json
Request:  { "phone_number": "+966500000001", "password": "SecurePass1!", "otp": "123456",
            "device_id": "device-uuid-abc", "device_name": "iPhone 15" }
Response: { "access": "eyJ...", "refresh": "eyJ...", "user": { "id": 1, "full_name": "Ali Hassan" } }
```

### POST `/api/auth/token/refresh/`
```json
Request:  { "refresh": "eyJ..." }
Response: { "access": "eyJ...", "refresh": "eyJ..." }
```

---

## Users (`/api/users/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/users/me/` | Yes | Get current user profile |
| PATCH | `/api/users/me/` | Yes | Update profile (full_name) |

### GET `/api/users/me/`
```json
Response: {
  "id": 1,
  "phone_number": "+966500000001",
  "full_name": "Ali Hassan",
  "status": "ACTIVE",
  "kyc_status": "APPROVED",
  "role": "CUSTOMER"
}
```

---

## Staff — Users (`/api/staff/`)

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| GET | `/api/staff/users/` | `view_all_users` | List all users |
| GET | `/api/staff/users/{id}/` | `view_all_users` | User detail |
| POST | `/api/staff/users/{id}/approve/` | `approve_user` | Approve pending user |
| POST | `/api/staff/users/{id}/reject/` | `reject_user` | Reject pending user |
| POST | `/api/staff/users/{id}/block/` | `block_user` | Block active user |
| POST | `/api/staff/users/{id}/unlock/` | `unlock_user` | Unlock locked user |

### POST `/api/staff/users/{id}/approve/`
```json
Request:  {}
Response: { "detail": "User approved.", "user": { "id": 1, "status": "ACTIVE" } }
```

---

## KYC (`/api/kyc/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/kyc/status/` | Yes | Get own KYC status + documents |
| POST | `/api/kyc/upload/` | Yes | Upload a KYC document |

### POST `/api/kyc/upload/`
```
Content-Type: multipart/form-data
Fields:
  document_type: NATIONAL_ID | PASSPORT | RESIDENCE_PERMIT | SELFIE | PROOF_OF_ADDRESS
  file: <binary>
```
```json
Response: { "id": 3, "document_type": "NATIONAL_ID", "status": "PENDING", "created_at": "..." }
```

## Staff — KYC (`/api/staff/kyc/`)

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| GET | `/api/staff/kyc/pending/` | `review_kyc` | List users with PENDING KYC |
| GET | `/api/staff/kyc/users/{id}/documents/` | `review_kyc` | User's KYC documents |
| POST | `/api/staff/kyc/users/{id}/approve/` | `review_kyc` | Approve user's KYC |
| POST | `/api/staff/kyc/users/{id}/reject/` | `review_kyc` | Reject user's KYC |
| POST | `/api/staff/kyc/documents/{id}/approve/` | `review_kyc` | Approve single document |
| POST | `/api/staff/kyc/documents/{id}/reject/` | `review_kyc` | Reject single document |

### POST `/api/staff/kyc/users/{id}/approve/`
```json
Request:  {}
Response: { "detail": "KYC approved." }
```

### POST `/api/staff/kyc/users/{id}/reject/`
```json
Request:  { "reason": "Document image is blurry" }
Response: { "detail": "KYC rejected." }
```

---

## Accounts (`/api/accounts/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/accounts/` | Yes | List own accounts |
| GET | `/api/accounts/{id}/` | Yes | Account detail + recent transactions |
| GET | `/api/accounts/beneficiaries/` | Yes | List beneficiaries |
| POST | `/api/accounts/beneficiaries/` | Yes | Add beneficiary |
| DELETE | `/api/accounts/beneficiaries/{id}/` | Yes | Remove beneficiary |

### GET `/api/accounts/`
```json
Response: [
  {
    "id": 1,
    "account_number": "6000000000000001",
    "account_name": "Ali Hassan - SAR",
    "currency": "SAR",
    "status": "ACTIVE",
    "available_balance": "4500.00",
    "ledger_balance": "4500.00"
  }
]
```

## Staff — Accounts (`/api/staff/accounts/`)

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| GET | `/api/staff/accounts/` | `view_all_accounts` | List all accounts |
| GET | `/api/staff/accounts/{id}/` | `view_all_accounts` | Account detail |
| POST | `/api/staff/accounts/{id}/freeze/` | `freeze_account` | Freeze account |
| POST | `/api/staff/accounts/{id}/unfreeze/` | `unfreeze_account` | Unfreeze account |
| POST | `/api/staff/accounts/{id}/block/` | `block_account` | Block account |

---

## Payments (`/api/payments/`)

### Transfers

| Method | Endpoint | Auth | KYC | Description |
|--------|----------|------|-----|-------------|
| POST | `/api/payments/transfer/otp/` | Yes | — | Request transfer OTP |
| POST | `/api/payments/transfer/` | Yes | Required | Execute transfer |

### POST `/api/payments/transfer/otp/`
```json
Request:  { "account_id": 1, "amount": "500.00" }
Response: { "detail": "OTP sent." }
```

### POST `/api/payments/transfer/`
```json
Request:  {
  "source_account_id": 1,
  "destination_account_number": "6000000000000002",
  "amount": "500.00",
  "currency": "SAR",
  "otp": "654321",
  "description": "Rent payment",
  "idempotency_key": "uuid-abc123"
}
Response: {
  "reference_number": "TXN2024000001",
  "status": "COMPLETED",
  "amount": "500.00",
  "fee": "5.00",
  "occurred_at": "2024-01-15T10:30:00Z"
}
```

### QR Payments

| Method | Endpoint | Auth | KYC | Description |
|--------|----------|------|-----|-------------|
| GET | `/api/payments/qr/{token}/` | Yes | — | Resolve QR details |
| POST | `/api/payments/qr/otp/` | Yes | — | Request QR payment OTP |
| POST | `/api/payments/qr/pay/` | Yes | Required | Execute QR payment |

### POST `/api/payments/qr/pay/`
```json
Request:  {
  "qr_token": "qr-token-uuid",
  "payer_account_id": 1,
  "amount": "250.00",
  "otp": "789012",
  "idempotency_key": "uuid-def456"
}
Response: {
  "reference_number": "TXN2024000002",
  "status": "COMPLETED",
  "amount": "250.00"
}
```

### Bill Payments

| Method | Endpoint | Auth | KYC | Description |
|--------|----------|------|-----|-------------|
| GET | `/api/payments/bill/providers/` | Yes | — | List bill providers |
| POST | `/api/payments/bill/fetch/` | Yes | — | Fetch bill details |
| POST | `/api/payments/bill/otp/` | Yes | — | Request bill payment OTP |
| POST | `/api/payments/bill/pay/` | Yes | Required | Execute bill payment |

### POST `/api/payments/bill/pay/`
```json
Request:  {
  "provider_code": "WATER_001",
  "service_number": "12345678",
  "payer_account_id": 1,
  "amount": "120.00",
  "otp": "345678",
  "idempotency_key": "uuid-ghi789"
}
Response: {
  "reference_number": "TXN2024000003",
  "status": "COMPLETED",
  "biller_amount": "120.00"
}
```

### Merchant (QR Generation)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/merchant/qr/generate/` | Yes | Generate QR code |
| GET | `/api/merchant/qr/` | Yes | List merchant QRs |

### POST `/api/merchant/qr/generate/`
```json
Request:  { "amount_mode": "FIXED", "display_amount": "250.00", "currency": "SAR" }
Response: {
  "qr_token": "tok_abc123...",
  "qr_payload": "safet://pay?token=tok_abc123...",
  "expires_at": "2024-01-15T11:30:00Z"
}
```

---

## Ledger (`/api/ledger/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/ledger/transactions/` | Yes | Own transaction history |
| GET | `/api/ledger/transactions/{ref}/` | Yes | Transaction detail |

## Staff — Ledger (`/api/staff/ledger/`)

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| GET | `/api/staff/ledger/transactions/` | `view_all_transactions` | All transactions |
| POST | `/api/staff/ledger/transactions/{ref}/reverse/` | `reverse_transaction` | Reverse transaction |

---

## Support (`/api/support/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/support/tickets/` | Yes | List own tickets |
| POST | `/api/support/tickets/` | Yes | Create ticket |
| GET | `/api/support/tickets/{id}/` | Yes | Ticket detail + messages |
| POST | `/api/support/tickets/{id}/reply/` | Yes | Add reply |
| POST | `/api/support/tickets/{id}/close/` | Yes | Close ticket |
| GET | `/api/support/notifications/` | Yes | List notifications |
| GET | `/api/support/notifications/unread-count/` | Yes | Unread count |
| POST | `/api/support/notifications/mark-all-read/` | Yes | Mark all read |
| PATCH | `/api/support/notifications/{id}/read/` | Yes | Mark one read |

### POST `/api/support/tickets/`
```json
Request:  { "subject": "Transfer issue", "category": "PAYMENT", "message": "My transfer is stuck." }
Response: { "id": 5, "status": "OPEN", "reference": "TKT-0005", "created_at": "..." }
```

## Staff — Support (`/api/staff/support/`)

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| GET | `/api/staff/support/tickets/` | `manage_support_tickets` | All tickets |
| GET | `/api/staff/support/tickets/{id}/` | `manage_support_tickets` | Ticket with internal notes |
| POST | `/api/staff/support/tickets/{id}/reply/` | `manage_support_tickets` | Reply (with `is_internal`) |
| POST | `/api/staff/support/tickets/{id}/assign/` | `manage_support_tickets` | Assign to agent |
| POST | `/api/staff/support/tickets/{id}/resolve/` | `manage_support_tickets` | Resolve ticket |
| POST | `/api/staff/support/tickets/{id}/close/` | `manage_support_tickets` | Close ticket |

---

## Risk (`/api/staff/risk/`)

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| GET | `/api/staff/risk/alerts/` | `review_fraud_alert` | List alerts (`?status=&severity=`) |
| GET | `/api/staff/risk/alerts/{id}/` | `review_fraud_alert` | Alert detail + decision |
| POST | `/api/staff/risk/alerts/{id}/review/` | `review_fraud_alert` | Submit decision |
| POST | `/api/staff/risk/alerts/{id}/dismiss/` | `review_fraud_alert` | Quick dismiss |

### POST `/api/staff/risk/alerts/{id}/review/`
```json
Request:  { "action": "FREEZE_ACCOUNT", "notes": "Confirmed fraudulent activity." }
Response: { "id": 7, "status": "ACTIONED", "decision": { "action": "FREEZE_ACCOUNT", ... } }
```

Valid actions: `DISMISS`, `WARN`, `FREEZE_ACCOUNT`, `BLOCK_ACCOUNT`, `ESCALATE`

---

## Reporting (`/api/staff/reports/`)

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| GET | `/api/staff/reports/admin/summary/` | `view_all_transactions` | Platform KPIs |
| GET | `/api/staff/reports/admin/users/growth/?days=30` | `view_all_users` | Daily new users |
| GET | `/api/staff/reports/admin/users/status/` | `view_all_users` | Users by status |
| GET | `/api/staff/reports/admin/transactions/volume/?period=daily&days=7` | `view_all_transactions` | Volume over time |
| GET | `/api/staff/reports/admin/transactions/by-type/?days=30` | `view_all_transactions` | Volume by type |
| GET | `/api/staff/reports/admin/fees/aggregate/?days=30` | `view_all_transactions` | Fee revenue |
| GET | `/api/staff/reports/risk/summary/` | `review_fraud_alert` | Risk KPIs |
| GET | `/api/staff/reports/risk/metrics/?days=30` | `review_fraud_alert` | Fraud time-series |
| GET | `/api/staff/reports/operations/summary/` | `review_kyc` or `manage_support_tickets` | Ops queue |
| GET | `/api/staff/reports/operations/transactions/recent/?limit=50` | `view_all_transactions` | Recent TX |
| GET | `/api/staff/reports/audit/transactions/{ref}/trace/` | `view_all_transactions` | Full TX trace |
| GET | `/api/staff/reports/audit/accounts/{id}/restrictions/` | `view_all_accounts` | Restriction history |
| GET | `/api/staff/reports/audit/risk/alerts/{id}/decisions/` | `review_fraud_alert` | Decision history |

### GET `/api/staff/reports/admin/summary/`
```json
Response: {
  "total_users": 1250,
  "active_users": 1100,
  "pending_users": 32,
  "blocked_users": 5,
  "total_transaction_count": 45230,
  "total_transaction_volume": "12500000.00",
  "total_available_balance": "8750000.00",
  "fee_revenue": "62500.00"
}
```

### GET `/api/staff/reports/audit/transactions/{ref}/trace/`
```json
Response: {
  "reference_number": "TXN2024000001",
  "transaction_type": "TRANSFER",
  "status": "COMPLETED",
  "amount": "500.00",
  "currency": "SAR",
  "risk_score": "15.00",
  "occurred_at": "2024-01-15T10:30:00Z",
  "entries": [
    { "entry_type": "DEBIT",  "amount": "505.00", "account_number": "6000000000000001" },
    { "entry_type": "CREDIT", "amount": "500.00", "account_number": "6000000000000002" },
    { "entry_type": "FEE",    "amount": "5.00",   "account_number": "FEE_POOL_ACCOUNT" }
  ],
  "reversals": [],
  "fraud_alerts": []
}
```

---

## Standard Error Responses

| HTTP Code | Meaning |
|---|---|
| 400 | Validation error — see `errors` object |
| 401 | Missing or expired JWT token |
| 403 | Authenticated but insufficient permission / KYC not approved |
| 404 | Resource not found |
| 409 | Conflict (e.g. duplicate review, already actioned) |
| 429 | Rate limit exceeded |

```json
{ "detail": "Your identity verification (KYC) is not yet approved." }
{ "errors": { "amount": ["This field is required."] } }
{ "detail": "Insufficient funds." }
```
