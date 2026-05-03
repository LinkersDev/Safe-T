# SafeT Backend — Database Schema

Database: **MySQL 8+**  
Charset: **utf8mb4**  
Collation: **utf8mb4_unicode_ci**  
All tables use **InnoDB** storage engine.

---

## Entity Relationship Overview

```
User ─────────────────────────────────────────────┐
  │  has Role                                      │
  │  has many Account                              │
  │  has many KycDocument                          │
  │  has many LoginLog                             │
  │  has many SupportTicket                        │
  │  has many FraudAlert                           │
  │                                                │
Account ──────────────────────────────────────────┤
  │  belongs to Currency                           │
  │  has many AccountRestriction                   │
  │  has many TransactionEntry                     │
  │                                                │
Transaction ─────────────────────────────────────┤
  │  has many TransactionEntry                     │
  │  has one  TransactionHistory                   │
  │  has one  QRPayment (optional)                 │
  │  has one  BillPayment (optional)               │
  │  has many FraudAlert                           │
  │                                                │
FraudAlert ──────────────────────────────────────┤
  │  has one  FraudDecision                        │
  │                                                │
SupportTicket ───────────────────────────────────┘
  has many SupportTicketMessage
```

---

## Core Models

### `users` table — User

| Column | Type | Notes |
|--------|------|-------|
| `id` | BigInt PK | auto-generated |
| `role_id` | FK → `roles` | nullable |
| `full_name` | VARCHAR(255) | |
| `phone_number` | VARCHAR(20) UNIQUE | login identifier |
| `phone_number_normalized` | VARCHAR(20) UNIQUE | stripped E.164 |
| `pin_hash` | VARCHAR(255) | argon2 hashed PIN |
| `status` | VARCHAR(30) | `PENDING_VERIFICATION` · `ACTIVE` · `REJECTED` · `BLOCKED` |
| `kyc_status` | VARCHAR(30) | `NOT_SUBMITTED` · `PENDING` · `APPROVED` · `REJECTED` |
| `is_phone_verified` | BOOLEAN | |
| `approved_by_id` | FK → `users` | nullable, staff who approved |
| `approved_at` | DATETIME | nullable |
| `rejection_reason` | TEXT | blank if not rejected |
| `blocked_reason` | TEXT | blank if not blocked |
| `is_staff` | BOOLEAN | Django admin access |
| `is_active` | BOOLEAN | Django auth active |
| `created_at` | DATETIME | auto |
| `updated_at` | DATETIME | auto |

**Indexes:** `phone_number_normalized`, `(role, status)`, `kyc_status`, `created_at`

---

### `accounts` table — Account

| Column | Type | Notes |
|--------|------|-------|
| `id` | BigInt PK | |
| `user_id` | FK → `users` | PROTECT |
| `currency_id` | FK → `currencies` | PROTECT |
| `account_number` | VARCHAR(34) UNIQUE | |
| `account_name` | VARCHAR(255) | |
| `status` | VARCHAR(20) | `ACTIVE` · `FROZEN` · `BLOCKED` · `CLOSED` |
| `available_balance` | DECIMAL(18,2) | immediately reflected on debit/credit |
| `ledger_balance` | DECIMAL(18,2) | total posted debits and credits |
| `blocked_amount` | DECIMAL(18,2) | reserved by HOLD entries |
| `opened_at` | DATETIME | auto |
| `closed_at` | DATETIME | nullable |

**Indexes:** `account_number`, `(user, status)`, `(currency, status)`

**Business rules:**
- `available_balance >= 0` always
- Only modified by `post_transaction()` inside an atomic block with `SELECT FOR UPDATE`

---

### `transactions` table — Transaction

| Column | Type | Notes |
|--------|------|-------|
| `id` | BigInt PK | |
| `reference_number` | VARCHAR(40) UNIQUE | e.g. `TXN20240001` |
| `transaction_type` | VARCHAR(20) | `TRANSFER` · `QR_PAYMENT` · `BILL_PAYMENT` · `DEPOSIT` · `WITHDRAWAL` |
| `status` | VARCHAR(20) | `PENDING` → `COMPLETED` · `FAILED` · `REVERSED` |
| `currency_id` | FK → `currencies` | PROTECT |
| `amount` | DECIMAL(18,2) | principal amount |
| `description` | VARCHAR(255) | |
| `channel` | VARCHAR(30) | `MOBILE` · `API` · `STAFF` · `SYSTEM` |
| `customer_id` | FK → `users` | nullable, SET_NULL |
| `initiated_by_id` | FK → `users` | nullable, SET_NULL |
| `idempotency_key` | VARCHAR(64) UNIQUE | nullable; prevents double-processing |
| `risk_score` | DECIMAL(5,2) | nullable; set by risk engine after commit |
| `parent_transaction_id` | FK → `transactions` | nullable; set for reversals |
| `occurred_at` | DATETIME | auto on creation |
| `completed_at` | DATETIME | nullable |
| `reversed_at` | DATETIME | nullable |
| `metadata_json` | JSON | payment-specific extras |

**Indexes:** `reference_number`, `(transaction_type, status)`, `occurred_at`,
`(customer, occurred_at)`, `idempotency_key`, `(status, occurred_at)`, `completed_at`

**Immutability:** Once `COMPLETED`, a transaction is never modified.
Corrections create a new `Transaction` with `parent_transaction` pointing to the original.

---

### `transaction_entries` table — TransactionEntry

| Column | Type | Notes |
|--------|------|-------|
| `id` | BigInt PK | |
| `transaction_id` | FK → `transactions` | PROTECT |
| `account_id` | FK → `accounts` | PROTECT |
| `entry_type` | VARCHAR(10) | `DEBIT` · `CREDIT` · `FEE` · `HOLD` · `RELEASE` |
| `amount` | DECIMAL(18,2) | |
| `sequence_no` | SmallInt | ordering within transaction |
| `created_at` | DATETIME | auto |

**Constraint:** `UNIQUE(transaction_id, sequence_no)`

**Double-entry invariant** (enforced by service):  
`SUM(DEBIT + FEE amounts) == SUM(CREDIT amounts)` for every COMPLETED transaction.

A typical transfer creates 3 entries:
```
seq 1: DEBIT  source_account    amount + fee
seq 2: CREDIT dest_account      amount
seq 3: FEE    fee_pool_account  fee
```

---

### `kyc_documents` table — KycDocument

| Column | Type | Notes |
|--------|------|-------|
| `id` | BigInt PK | |
| `user_id` | FK → `users` | CASCADE |
| `document_type` | VARCHAR(50) | `NATIONAL_ID` · `PASSPORT` · `SELFIE` etc. |
| `file` | FileField | stored under `media/kyc_documents/YYYY/MM/` |
| `status` | VARCHAR(20) | `PENDING` · `APPROVED` · `REJECTED` |
| `reviewed_by_id` | FK → `users` | nullable, SET_NULL |
| `reviewed_at` | DATETIME | nullable |
| `rejection_reason` | TEXT | blank if approved |
| `notes` | TEXT | staff notes |
| `created_at` | DATETIME | auto |
| `updated_at` | DATETIME | auto |

---

### `fraud_alerts` table — FraudAlert

| Column | Type | Notes |
|--------|------|-------|
| `id` | BigInt PK | |
| `alert_type` | VARCHAR(20) | `TRANSACTION` · `LOGIN` |
| `severity` | VARCHAR(20) | `LOW` · `MEDIUM` · `HIGH` · `CRITICAL` |
| `status` | VARCHAR(20) | `OPEN` · `REVIEWED` · `DISMISSED` · `ACTIONED` |
| `risk_score` | DECIMAL(5,2) | computed by rules engine |
| `user_id` | FK → `users` | nullable, SET_NULL |
| `account_id` | FK → `accounts` | nullable, SET_NULL |
| `transaction_id` | FK → `transactions` | nullable, SET_NULL |
| `login_log_id` | FK → `login_logs` | nullable, SET_NULL |
| `rules_triggered` | JSON | list of rule reason strings |
| `auto_action_taken` | VARCHAR(50) | e.g. `ACCOUNT_FROZEN`; blank if manual |
| `reviewed_by_id` | FK → `users` | nullable |
| `reviewed_at` | DATETIME | nullable |
| `created_at` | DATETIME | auto |
| `updated_at` | DATETIME | auto |

**Indexes:** `(status, severity)`, `(user, created_at)`

---

### `fraud_decisions` table — FraudDecision

| Column | Type | Notes |
|--------|------|-------|
| `id` | BigInt PK | |
| `alert_id` | FK → `fraud_alerts` OneToOne | CASCADE |
| `officer_id` | FK → `users` | nullable, SET_NULL |
| `action` | VARCHAR(30) | `DISMISS` · `WARN` · `FREEZE_ACCOUNT` · `BLOCK_ACCOUNT` · `ESCALATE` |
| `notes` | TEXT | |
| `executed_at` | DATETIME | auto |

---

## Supporting Models

### `roles` / `permissions` / `role_permissions`

Custom RBAC system. Staff roles and their allowed actions are defined at deploy time.

```
Role (code, name, is_staff_role)
  └─ RolePermission (role_id, permission_id)
       └─ Permission (code, name, module)

User.role_id → Role
```

Pre-seeded roles: `CUSTOMER`, `ADMIN`, `TELLER`, `TELLER_ADMIN`, `CUSTOMER_SERVICE`, `RISK_OFFICER`, `MERCHANT_CUSTOMER`

---

### `currencies` — Currency

ISO 4217. Primary key is the 3-letter code (`SAR`). Seeded by migration.

---

### `account_restrictions` — AccountRestriction

Append-only log of every FREEZE/BLOCK event on an account. The `is_active` flag
indicates the current effective restriction. Account.status is always kept in sync.

---

### `transaction_history` — TransactionHistory

Immutable snapshot written once after a transaction reaches `COMPLETED`.
Denormalised for efficient reporting without heavy JOINs.

---

## Index Strategy

All foreign key columns are indexed by Django automatically.  
Additional composite indexes are placed on the most common query patterns:

| Table | Index | Purpose |
|---|---|---|
| transactions | `(status, occurred_at)` | Reporting: completed TX by period |
| transactions | `occurred_at` | Time-series aggregations |
| transactions | `(customer, occurred_at)` | User transaction history |
| fraud_alerts | `(status, severity)` | Risk Officer alert queue |
| fraud_alerts | `(user, created_at)` | Per-user fraud history |
| account_restrictions | `(account, is_active)` | Active restriction lookup |
| kyc_documents | `(user, status)` | KYC review queue |
