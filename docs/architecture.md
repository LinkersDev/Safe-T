# SafeT Backend Architecture

## System Overview
SafeT is designed as a Django + DRF backend for a mobile banking platform with branch operations, merchant payments, support operations, and risk monitoring. The architecture is centered on a ledger-first transaction engine, strong authentication, auditable staff actions, and explicit risk review records.

## Django App Structure

### `users`
- custom user model
- roles and permissions
- phone-number identity
- approval and activation lifecycle

### `kyc`
- customer document storage metadata
- KYC review workflow
- approval and rejection records

### `accounts`
- customer and merchant bank accounts
- account status management
- beneficiary management
- account restriction history

### `ledger`
- transaction header model
- transaction entry model
- transaction history archive
- fee rules
- posting and reversal services

### `payments`
- merchant profile management
- QR payment records
- bill provider setup
- bill payment records

### `security`
- OTP issuance and verification audit
- login logs
- device registry
- account lock events
- password and PIN reset audit

### `support`
- complaint and assistance tickets
- internal and customer-facing notifications

### `risk`
- fraud alerts
- fraud review decisions
- account restriction integration

### `api`
- DRF viewsets, serializers, permissions, throttling, and API contracts

### `reporting`
- query services and exported operational reports

## Core Design Rules
- Phone number is the single login identifier.
- All funds movement must pass through the ledger.
- Business workflows create channel-specific records (`QRPayment`, `BillPayment`) around a common `Transaction`.
- Customer onboarding is hybrid:
  - self-registration
  - pending access
  - teller/admin activation
- Financial restrictions and login restrictions are separate concerns:
  - `AccountRestriction` for money movement
  - `AccountLockEvent` for access/security lock state

## Suggested Service Layers

### Identity services
- registration service
- OTP verification service
- approval service
- password/PIN management service

### Ledger services
- transaction posting service
- fee application service
- reversal service
- balance projection service

### Payments services
- transfer service
- QR payment service
- bill payment service

### Risk services
- feature collection service
- fraud scoring adapter
- risk review service
- account restriction orchestration

### Support services
- ticket management service
- notification dispatcher

## API and Security Notes
- Use DRF authentication suitable for mobile clients.
- Enforce OTP for high-risk actions.
- Add throttling for login, OTP, and transaction endpoints.
- Use object-level permission checks for staff workflows.
- Log all security-sensitive actions.
- Never expose internal ledger entries directly without an access control layer.

## Data Integrity Notes
- Use database transactions for posting all ledger operations.
- Lock affected account rows during posting.
- Enforce idempotency for client-submitted payment requests.
- Keep completed transactions immutable.
- Use append-only audit models for restrictions, resets, and fraud outcomes.

## AI Readiness
- Keep OTP, login, device, restriction, and transaction data queryable.
- Store fraud scores and reviewed outcomes separately.
- Preserve timestamps and actor references on all critical operations.
- Add asynchronous event publishing later for fraud pipelines without changing the schema core.
