# SafeT Frontend Plan (Web-Only Now, Mobile-Ready Later)

## Strategy Decision

- Build **web application only** in this phase.
- Do **not** implement PWA, service workers, or Capacitor now.
- Keep architecture platform-agnostic so PWA and mobile wrappers can be added with minimal refactor.

## Scope Boundaries (Current Phase)

- Included now:
  - React 18 + TypeScript + Vite.
  - Tailwind CSS.
  - React Router v6.
  - TanStack Query.
  - Rule-driven app architecture from prior audit.
  - Sample implemented flows in future execution phase: Auth (login + OTP), Transfer payment.
- Explicitly excluded now:
  - Service worker registration.
  - `vite-plugin-pwa`.
  - Capacitor setup/files.
  - Direct camera/native notification integrations.

---

## Rule Baseline (Normalized)

Rules remain authoritative and unchanged in intent; grouped for implementation.

### Authentication and Security

- `RULE-001` Phone number is sole login identity.
- `RULE-002` Registration/login/reset rely on OTP verification.
- `RULE-003` OTP lifecycle: expiry + max attempts + resend throttling.
- `RULE-004` Session lifecycle: access+refresh, one retry on 401 then logout.
- `RULE-005` Account states impact login outcome (locked/blocked).
- `RULE-006` Device context is required in auth payloads.

### KYC

- `RULE-007` KYC status model: `NOT_SUBMITTED`, `PENDING`, `APPROVED`, `REJECTED`.
- `RULE-008` Financial execution requires KYC approved.
- `RULE-009` Rejected KYC can re-upload and return to pending.

### Accounts

- `RULE-010` Account status model: `ACTIVE`, `FROZEN`, `BLOCKED`, `CLOSED`.
- `RULE-011` Debit-origin actions forbidden for non-active debit statuses.
- `RULE-012` Beneficiary constraints: valid destination, no self-account, duplicate conflict handling.

### Ledger and Transactions

- `RULE-013` Every money movement maps to ledger transaction references.
- `RULE-014` Transaction states: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `REVERSED`, `CANCELLED`.
- `RULE-015` Completed transaction is immutable; correction via reversal.
- `RULE-016` Idempotency key required for financial submission safety.

### Payments (Transfer, QR, Bills)

- `RULE-017` Transfer: OTP step then execute step with idempotency key.
- `RULE-018` QR: resolve token, OTP, execute; handle expired/already-paid.
- `RULE-019` Bill: provider list, fetch, OTP, execute.

### Staff and Permissions

- `RULE-020` Role set includes 7 roles.
- `RULE-021` Route and action visibility must be permission-aware (not role-label only).
- `RULE-022` Backend mixes role checks and permission checks; frontend must defend both.

### Risk and Fraud

- `RULE-023` Alert severities and review lifecycle drive staff UI.
- `RULE-024` Critical flows may trigger automatic restriction outcomes.

### Support and Notifications

- `RULE-025` Ticket lifecycle states control allowed replies/actions.
- `RULE-026` Internal notes are staff-only.
- `RULE-027` Notifications are eventually consistent; unread/read controls required.

---

## Rule to UX Impact Matrix (Implementation Contract)

- `RULE-001..006` (Auth/Security):
  - Must show OTP timers, lock/blocked explanations, session expiry behavior.
  - Must block protected navigation on invalid session.
  - Must never expose account-existence details via UI wording.

- `RULE-007..009` (KYC):
  - Must show KYC status globally in payment entry points.
  - Must block transfer execution when not approved.
  - Must route rejected users to re-upload path.

- `RULE-010..012` (Accounts):
  - Must hide/disable debit source accounts that are not eligible.
  - Must reject self-account beneficiary creation in UI pre-validation.

- `RULE-013..016` (Ledger/Transactions):
  - Must show transaction reference and terminal status mapping.
  - Must preserve idempotency key across retries for the same attempt.

- `RULE-017..019` (Payments):
  - Must enforce strict flow sequence (precheck -> OTP -> execute).
  - Must display domain-specific failure reasons (expired QR, provider invalid, insufficient funds).

- `RULE-020..022` (Staff/Permissions):
  - Must guard route, section, and action separately.
  - Must handle backend inconsistency with safe 403 fallback.

- `RULE-023..024` (Risk):
  - Must represent alert status as immutable once reviewed/actioned.

- `RULE-025..027` (Support):
  - Must disable customer reply outside active ticket states.
  - Must keep internal notes hidden from customer views.
  - Must support polling/refresh for notification eventual consistency.

---

## Web-Only Architecture (Prepared for PWA/Capacitor)

### Required Project Skeleton

- `src/app`
  - `bootstrap/`
  - `routing/`
  - `providers/`
- `src/core`
  - `api/`
  - `auth/`
  - `platform/`
  - `permissions/`
  - `rules/`
  - `state/`
  - `utils/`
- `src/domains`
  - `security/`
  - `kyc/`
  - `accounts/`
  - `ledger/`
  - `payments-transfer/`
  - `payments-qr/`
  - `payments-bills/`
  - `merchant/`
  - `support/`
  - `risk/`
  - `staff-users/`
  - `staff-accounts/`
  - `staff-ledger/`
  - `staff-reporting/`
- `src/shared`
  - `components/`
  - `forms/`
  - `layouts/`
  - `styles/`

### Core Technology Decisions (Now)

- React 18 + TypeScript + Vite.
- React Router v6.
- TanStack Query for server state.
- Tailwind CSS for responsive-first UI.
- No PWA/Capacitor packages in this phase.

---

## Platform Abstraction Layer (Mandatory for Future Mobile)

Create `src/core/platform/` with interfaces and web adapters:

- `storage/`
  - `TokenStorage` interface:
    - `readAccessToken()`
    - `readRefreshToken()`
    - `saveTokens()`
    - `clearTokens()`
  - Web adapter uses browser storage now.
  - Future adapter swaps to secure mobile storage without touching domain code.

- `device/`
  - `DeviceIdentity` interface:
    - `getDeviceId()`
    - `getDeviceName()`
  - Web adapter generates stable persisted `device_id`.
  - Future mobile adapter can map to native device identifier.

- `camera/`
  - Placeholder interface for future QR camera integration.
  - Current web implementation returns `not_implemented` error contract.

- `notifications/`
  - Placeholder interface for native push/local notifications.
  - Current phase uses backend polling only.

---

## API Layer and Financial Safety (Web Phase)

### API Client Requirements

- Single Axios instance in `src/core/api/`.
- Request interceptor:
  - Attach bearer token and device headers.
- Response interceptor:
  - On 401: attempt refresh once, replay original request once, then logout.
- Error normalization:
  - Normalize `detail`, field `errors`, status code, and unknown payload shape.

### Idempotency Strategy

- `src/core/api/idempotency.ts`:
  - Generate UUID per financial attempt.
  - Persist key in in-memory flow state for active attempt.
  - Reuse same key on retry for that exact pending/failed attempt.
  - Clear key only on terminal outcome confirmation.

---

## Routing and Guard System

Guards implemented as composable route wrappers:

- `AuthGuard`: requires valid session.
- `RoleGuard`: checks coarse role eligibility.
- `PermissionGuard`: checks permission capability matrix.
- `RuleGuard`: runtime business gates (KYC approved, account eligible, etc.).

Guard priority:
1. `AuthGuard`
2. `RoleGuard`/`PermissionGuard`
3. `RuleGuard`

---

## Responsive-First UI Contract

- Mobile-first layout defaults (small viewport first, progressive enhancement).
- No fixed pixel-width containers for critical flows.
- Touch-friendly controls:
  - minimum interactive target sizing.
  - spacing designed for thumb operation.
- Critical financial actions pinned in reachable UI zones on small screens.

---

## Screen Set for Current Implementation Phase

### Must Implement First (Web)

- Auth:
  - Login Phone Screen.
  - Login OTP Screen.
  - Credential Submission Screen (password/PIN).
- Transfer:
  - Transfer Form Screen.
  - Transfer OTP Confirmation Screen.
  - Transfer Result Screen (success/fail/reconcile).

### Must Scaffold (No Full Business Completion Yet)

- KYC Status page.
- Accounts list/detail shell.
- Ledger history shell.
- Support/notifications shell.
- Staff shell routes and placeholder module entries.

---

## Backend Inconsistency Handling (Safety Policies)

- `INC-001` Mixed role vs permission checks:
  - Guard by both in UI and tolerate backend 403 with deterministic fallback UX.
- `INC-002` `TELLER_ADMIN` ambiguity:
  - Hide potentially unsupported actions by explicit endpoint capability flags.
- `INC-003` Fee-rules endpoint instability:
  - Hide behind feature flag until backend fix is verified.
- `INC-004` KYC aggregate vs document-level mismatch:
  - Use KYC status endpoint as execution gate source of truth.
- `INC-005` Error payload variability:
  - Avoid string-equality logic; rely on code/status class mapping.

---

## Execution Plan (Web-Only, Future-Ready)

### Phase 1: Foundation

- Initialize Vite React TS app.
- Add Tailwind, Router, Query.
- Create strict folder structure and module boundaries.
- Build core platform abstraction interfaces (storage/device/camera/notifications).

### Phase 2: Core Infrastructure

- Implement token storage abstraction (web adapter only).
- Implement API client with refresh retry and error normalizer.
- Implement device ID abstraction and stable generation.
- Implement route guards (`AuthGuard`, `RoleGuard`, `PermissionGuard`, `RuleGuard`).

### Phase 3: Auth Flow (Sample)

- Implement login + OTP flow end-to-end.
- Integrate session state and guarded route entry.

### Phase 4: Transfer Flow (Sample)

- Implement transfer flow with idempotency key lifecycle.
- Add duplicate-submit prevention and retry-with-same-key behavior.
- Add reconcile state for uncertain outcomes.

### Phase 5: Responsive Hardening

- Apply mobile-first layout tuning to all current screens.
- Validate touch affordances and small-screen behavior.

### Phase 6: Future Migration Readiness Check

- Verify no direct browser API usage outside `src/core/platform/`.
- Verify no PWA/Capacitor coupling in domain code.
- Document adapters to add later for PWA/Capacitor.

---

## Future Upgrade Path (Not Implemented Now)

When upgrading later:

- PWA:
  - Add service worker and caching strategy in app bootstrap layer only.
  - Keep domain/application code unchanged.
- Capacitor:
  - Add native shell and replace web adapters in `src/core/platform/`.
  - Keep auth, API, rules, and domain modules unchanged.

---

## Non-Negotiable Constraints

- No PWA plugin or service worker in this phase.
- No Capacitor setup in this phase.
- No direct browser-specific calls in domain/business logic.
- All platform-specific operations must go through `src/core/platform/`.
- Financial flows must preserve idempotency key safety and prevent duplicate submission.
