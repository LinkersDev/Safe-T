# SafeT — Mobile Banking Backend

A production-quality Django REST Framework backend for the SafeT mobile banking system.

---

## Features

| Module | Capabilities |
|---|---|
| **Users & Auth** | Phone-only registration, OTP login, JWT tokens, device tracking |
| **KYC** | Document upload, staff review workflow, financial access gating |
| **Accounts** | Multi-currency accounts, beneficiaries, freeze/block controls |
| **Ledger** | Double-entry bookkeeping, atomic transfers, fee engine, idempotency |
| **Payments** | Peer-to-peer transfers, QR payments, bill payments |
| **Support** | Customer tickets, staff replies, internal notes, in-app notifications |
| **Risk** | Rule-based fraud scoring, auto-freeze on CRITICAL, Risk Officer review |
| **Reporting** | Admin/Risk/Ops dashboards, time-series reports, full audit traces |

---

## Tech Stack

- **Python 3.12+** / **Django 6+** / **Django REST Framework 3.17+**
- **MySQL 8+** via **PyMySQL** (charset utf8mb4, STRICT_TRANS_TABLES)
- **JWT** via `djangorestframework-simplejwt`
- **argon2** password and OTP hashing
- **SQLite** for tests (in-memory, no MySQL required for CI)

---

## Project Structure

```
backend/
├── manage.py
├── config/
│   ├── __init__.py        ← PyMySQL installation
│   ├── settings/
│   │   ├── base.py        ← shared settings
│   │   └── test.py        ← test overrides (SQLite in-memory)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── users/             ← identity, roles, permissions
│   ├── security/          ← OTP, login logs, device tracking, locks
│   ├── kyc/               ← document upload & staff review
│   ├── accounts/          ← bank accounts, restrictions, beneficiaries
│   ├── ledger/            ← double-entry transactions, fee rules
│   ├── payments/          ← transfers, QR, bill payments
│   ├── support/           ← tickets & in-app notifications
│   ├── risk/              ← fraud scoring & Risk Officer review
│   └── reporting/         ← read-only dashboards & audit views
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── scripts/
│   ├── setup_db.sh
│   ├── run_server.sh
│   └── run_tests.sh
├── docs/
│   ├── architecture.md
│   ├── api_overview.md
│   ├── frontend_guide.md
│   ├── database_schema.md
│   └── workflows.md
└── media/                 ← user-uploaded files (KYC documents)
```

---

## Quick Start

### 1. Prerequisites

- Python 3.12+
- MySQL 8+ running locally (or use Docker)
- pip

### 2. Clone and set up Python environment

```bash
git clone <repo-url>
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here

DB_NAME=safet_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306

ACCESS_TOKEN_LIFETIME_MINUTES=15
REFRESH_TOKEN_LIFETIME_DAYS=7
LEDGER_FEE_POOL_ACCOUNT_NUMBER=
```

### 4. Set up database

```bash
bash scripts/setup_db.sh
```

This will:
- Create the `safet_db` database (utf8mb4)
- Run all Django migrations
- Create a default superuser (`+966500000000` / `Admin1234!`)

### 5. Run development server

```bash
bash scripts/run_server.sh
# or: python manage.py runserver --settings=config.settings.base
```

API: `http://localhost:8000/`  
Admin: `http://localhost:8000/admin/`

---

## Running Tests

Tests use an in-memory SQLite database — **no MySQL required**.

```bash
# Run all tests
bash scripts/run_tests.sh

# Run a specific app
bash scripts/run_tests.sh apps.ledger
bash scripts/run_tests.sh apps.risk
bash scripts/run_tests.sh apps.reporting

# Direct command
python manage.py test --settings=config.settings.test --verbosity=2
```

**Test coverage:** 378 tests across all apps including:
- Unit tests for all service and selector functions
- Integration tests for all API endpoints
- Concurrency / stress tests (double-spend, OTP replay, QR race)
- KYC enforcement and auto-freeze tests

---

## Django Admin

Access at `http://localhost:8000/admin/` with superuser credentials.

All models are registered with:
- Useful `list_display`, search, and filters
- `date_hierarchy` for time-based browsing on key models
- Financial models (`Transaction`, `TransactionEntry`, `TransactionHistory`) are
  **fully read-only** in admin — no accidental mutations possible

---

## API Documentation

See [`docs/api_overview.md`](docs/api_overview.md) for a complete endpoint reference.

See [`docs/frontend_guide.md`](docs/frontend_guide.md) for frontend integration flows
including authentication, KYC, transfers, QR payments, and bill payments.

---

## Security Notes

- All financial operations require `kyc_status == APPROVED` (enforced at both
  the DRF permission layer and inside `post_transaction()`)
- OTPs are argon2-hashed, expire in 10 minutes, and are single-use
- Money transfers use `SELECT FOR UPDATE` — no double-spend possible
- Risk engine auto-freezes accounts on CRITICAL fraud score (≥75 points)
- All login attempts are logged; accounts auto-lock after 5 failed attempts
- JWT access tokens expire in 15 minutes; refresh tokens rotate on use

---

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for:
- App responsibilities and separation of concerns
- Service / selector pattern
- Transaction flow with double-entry invariants
- KYC enforcement layers
- Risk engine design
