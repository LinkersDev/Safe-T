# SafeT Backend — Architecture

## 1. Project Layout

```
backend/
├── manage.py
├── config/                     ← Django configuration package
│   ├── __init__.py             ← PyMySQL installation (runs before settings)
│   ├── settings/
│   │   ├── base.py             ← shared settings (DB, apps, JWT, throttle)
│   │   └── test.py             ← test overrides (SQLite in-memory, no throttle)
│   ├── urls.py                 ← root URL aggregator
│   ├── wsgi.py
│   └── asgi.py
├── apps/                       ← all business-domain apps
│   ├── users/                  ← identity, roles, permissions
│   ├── security/               ← OTP, login, device tracking, locks
│   ├── kyc/                    ← document upload & staff review
│   ├── accounts/               ← bank accounts, restrictions, beneficiaries
│   ├── ledger/                 ← double-entry transactions, fees
│   ├── payments/               ← transfers, QR payments, bill payments
│   ├── support/                ← tickets & in-app notifications
│   ├── risk/                   ← fraud detection & Risk Officer review
│   └── reporting/              ← read-only dashboards & audit views
├── requirements/
│   ├── base.txt                ← production dependencies
│   ├── dev.txt                 ← dev + test extras
│   └── prod.txt                ← production-only extras
├── scripts/                    ← operational shell scripts
├── docs/                       ← this folder
└── media/                      ← user-uploaded files (KYC documents)
```

---

## 2. App Responsibilities

| App | Owns | Does NOT own |
|---|---|---|
| `users` | User model, Roles, Permissions | Authentication |
| `security` | OTP, LoginLog, UserDevice, Locks | User identity |
| `kyc` | KycDocument, review flow | Financial operations |
| `accounts` | Account, Currency, AccountRestriction, Beneficiary | Ledger math |
| `ledger` | Transaction, TransactionEntry, FeeRule, post_transaction | Payment-type routing |
| `payments` | MerchantProfile, QRPayment, BillProvider, BillPayment | Core ledger |
| `support` | SupportTicket, Notification | Risk scoring |
| `risk` | FraudAlert, FraudDecision, scoring rules | Account management |
| `reporting` | Dashboard selectors, audit views | Any writes |

---

## 3. Service / Selector Pattern

Every app follows a strict layered structure:

```
HTTP Request
    ↓
views.py          (permission check → call selector or service)
    ↓
services.py       (write path — atomic, validated, guarded)
    ↓             OR
selectors.py      (read path — aggregated, optimised queries)
    ↓
models.py         (ORM — no business logic)
    ↓
Database
```

**Rules:**
- Views contain NO business logic — only permission checks and serialisation.
- Services execute ALL writes inside `django.db.transaction.atomic()`.
- Selectors never write. Views call them directly for read-only responses.
- Exceptions raised by services are domain-specific (e.g. `InsufficientFundsError`),
  caught in views and mapped to HTTP status codes.

---

## 4. Transaction Flow (`post_transaction`)

`apps/ledger/services.py::post_transaction` is the single entry point for all monetary operations.

```
post_transaction(
    transaction_type,   # TRANSFER | QR_PAYMENT | BILL_PAYMENT | ...
    currency_code,
    amount,
    source_account,
    destination_account,
    customer,
    idempotency_key,    # prevents duplicate submissions
)
```

### Internal flow

```
1. Idempotency check         — reject duplicate reference
2. _assert_user_active()     — PENDING_VERIFICATION users blocked
3. _assert_kyc_approved()    — non-APPROVED KYC blocked (defence-in-depth)
4. assert_account_can_debit() — FROZEN / BLOCKED / CLOSED accounts blocked
5. BEGIN ATOMIC BLOCK
   ├─ SELECT ... FOR UPDATE on source_account (prevents double-spend)
   ├─ SELECT ... FOR UPDATE on dest_account   (prevents race)
   ├─ Re-check balance inside lock
   ├─ calculate_fee()         — apply FeeRule if active
   ├─ Debit source            — available_balance -= (amount + fee)
   ├─ Credit destination      — available_balance += amount
   ├─ Credit fee pool         — available_balance += fee (if configured)
   ├─ Create TransactionEntry records (DEBIT, CREDIT, FEE)
   ├─ Create TransactionHistory snapshot
   └─ Commit
6. on_commit → dispatch_post_transaction_notifications()
7. on_commit → score_transaction()    ← risk engine
8. return Transaction
```

**Guarantees:**
- Balance never goes negative — enforced by lock + re-check inside atomic block.
- Double-entry always balanced — SUM(DEBIT + FEE) == SUM(CREDIT) for every transaction.
- Idempotent — duplicate idempotency_key returns the original transaction.
- Atomic — any failure rolls back all entries and balance changes.

---

## 5. KYC Enforcement (Defence-in-Depth)

KYC is enforced at **two independent layers**:

```
Layer 1 — DRF permission class
  applied to: transfer_execute, qr_pay_execute, bill_pay_execute
  class: apps.kyc.permissions.IsKYCApproved
  rejects with: HTTP 403 if user.kyc_status != APPROVED

Layer 2 — Service guard  (inside post_transaction)
  function: _assert_kyc_approved(customer)
  rejects with: KYCNotApprovedError
  purpose: blocks direct service-layer calls that bypass the view layer
```

Even if the view-layer permission is misconfigured or the service is called
programmatically (e.g., from a management command), the transaction will be
rejected unless KYC is APPROVED.

---

## 6. Risk Engine

```
Event occurs
    │
    ├─ Transaction committed
    │       └─ on_commit → score_transaction(tx_pk)
    │               └─ rules.compute_transaction_score()
    │                      rules: amount threshold, velocity, abnormal hour
    │               └─ Transaction.risk_score updated
    │               └─ score >= 25 → FraudAlert created
    │               └─ score >= 75 (CRITICAL) → account auto-frozen
    │
    └─ Login recorded
            └─ score_login(login_log_pk) [synchronous, try/except]
                    └─ rules.compute_login_score()
                           rules: failed attempts, new device, new country, abnormal hour
                    └─ LoginLog.risk_score updated
                    └─ score >= 25 → FraudAlert created

FraudAlert (OPEN)
    └─ Risk Officer: POST /api/staff/risk/alerts/{id}/review/
            action=DISMISS       → alert DISMISSED
            action=WARN          → alert REVIEWED
            action=FREEZE_ACCOUNT → account frozen + alert ACTIONED
            action=BLOCK_ACCOUNT  → account blocked + alert ACTIONED
```

**Critical invariant:** Scoring failure (exception in score_transaction or score_login)
is swallowed — it NEVER affects the committed transaction or the login response.

---

## 7. Database

- **Engine:** MySQL 8+ via PyMySQL (`pymysql.install_as_MySQLdb()`)
- **Charset:** utf8mb4 / utf8mb4_unicode_ci on all tables
- **Mode:** STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO
- **Financial fields:** All monetary values use `DecimalField(max_digits=18, decimal_places=2)`
- **Concurrency:** `SELECT ... FOR UPDATE` (InnoDB row-level locking) inside `atomic()`
- **Tests:** In-memory SQLite (via `config.settings.test`) — no MySQL required for CI

---

## 8. Security Layers

| Layer | Mechanism |
|---|---|
| Authentication | JWT Bearer token (access 15 min, refresh 7 days) |
| OTP | argon2-hashed, time-limited, single-use, rate-limited |
| KYC guard | `IsKYCApproved` permission class + `_assert_kyc_approved` service guard |
| User status guard | `IsUserFullyActive` permission class |
| RBAC | Custom `Role → Permission → RolePermission` (no Django groups) |
| Throttling | Per-IP for OTP/login; per-user for transfers |
| Account lock | Auto-lock after N failed logins; staff unlock endpoint |
| Audit trail | `LoginLog`, `AccountRestriction`, `TransactionHistory`, `FraudDecision` |
