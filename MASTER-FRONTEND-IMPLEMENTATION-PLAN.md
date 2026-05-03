# MASTER FRONTEND IMPLEMENTATION PLAN

## 1. System Overview

SafeT frontend is a **web-only, mobile-first, rule-driven fintech application** built around strict backend contracts and financial safety constraints.  
Architecture combines:
- Domain isolation (`auth/security`, `kyc`, `accounts`, `ledger`, `payments-transfer`, `payments-qr`, `payments-bills`, `support`, `risk`, `staff`).
- Centralized guards (`AuthGuard`, `RoleGuard`, `PermissionGuard`, `RuleGuard`).
- Defensive API layer (token refresh, error normalization, idempotency safety).
- Shared UI/UX design system (semantic tokens, reusable components, security-safe patterns).

Key constraints:
- Web implementation only in current scope.
- No PWA plugin, service worker, or Capacitor setup now.
- No direct platform-specific API usage in business domains.
- Fintech safety is mandatory: idempotency, status-gated actions, non-revealing errors, reconciliation paths.

---

## 2. Domain Breakdown (Backend + Plan + Design System)

## Auth and Security
- **Purpose**: secure identity flow, session lifecycle, OTP-based verification, safe recovery.
- **Key rules**: `RULE-001` to `RULE-006`.
- **UI dependencies**:
  - OTP segmented input, input states, button loading/disabled states.
  - Security-safe alert patterns, session-expired modal/banner, toast for non-critical feedback.
- **Required APIs (high-level)**:
  - Auth registration/login OTP endpoints.
  - Login execution and token refresh.
  - Password/PIN reset send/confirm endpoints.

## KYC
- **Purpose**: enforce onboarding and financial eligibility gates.
- **Key rules**: `RULE-007` to `RULE-009`.
- **UI dependencies**:
  - Status badges, warning banners, upload card/form patterns.
  - Restricted action UI pattern for non-approved states.
- **Required APIs**:
  - KYC status.
  - KYC upload.
  - Staff KYC review endpoints (for staff module).

## Accounts
- **Purpose**: account visibility, status-aware action gating, beneficiary management.
- **Key rules**: `RULE-010` to `RULE-012`.
- **UI dependencies**:
  - Balance cards, account status badges, form validation for beneficiary entry.
  - Disabled action states with explanatory copy.
- **Required APIs**:
  - Accounts list/detail.
  - Beneficiary CRUD.
  - Staff account control APIs.

## Ledger and Transactions
- **Purpose**: immutable transaction history, status rendering, reversal awareness.
- **Key rules**: `RULE-013` to `RULE-016`.
- **UI dependencies**:
  - Transaction list item pattern, receipt pattern, state machine badges.
  - Skeleton loaders for history and detail.
- **Required APIs**:
  - Customer ledger list/detail.
  - Staff ledger list/detail/reverse/archive.

## Payments (Transfer, QR, Bills)
- **Purpose**: secure transaction execution via wizarded flows.
- **Key rules**: `RULE-017` to `RULE-019` plus `RULE-016`.
- **UI dependencies**:
  - Amount input, OTP input, confirmation layout, fee breakdown panel, sticky action bars.
  - Failure/retry/reconcile UX.
- **Required APIs**:
  - Transfer OTP + execute.
  - QR resolve + OTP + execute.
  - Bill providers + fetch + OTP + execute.

## Support and Notifications
- **Purpose**: customer support operations and event communication.
- **Key rules**: `RULE-025` to `RULE-027`.
- **UI dependencies**:
  - Ticket status badges, ticket thread cards, notification center with read states.
  - Internal-note visibility restrictions for staff/customer split.
- **Required APIs**:
  - Ticket list/detail/reply/close.
  - Notification list/unread/read-one/read-all.
  - Staff support management endpoints.

## Staff Panel
- **Purpose**: role-permission-governed operational tooling.
- **Key rules**: `RULE-020` to `RULE-022`.
- **UI dependencies**:
  - Permission-gated navigation, admin tables/cards, modal confirmations for critical actions.
- **Required APIs**:
  - Staff users, KYC, accounts, ledger, support, reports.

## Risk Module
- **Purpose**: fraud alert triage and decisioning.
- **Key rules**: `RULE-023`, `RULE-024`.
- **UI dependencies**:
  - Severity badges, alert detail card, terminal-state action lock.
  - Blocked/risk warning UI pattern.
- **Required APIs**:
  - Risk alerts list/detail/review/dismiss.
  - Risk report endpoints.

---

## 3. Phased Implementation Plan

## Phase 1: Foundation
- Initialize web stack (React 18, TypeScript, Vite, Tailwind, Router, TanStack Query).
- Create architecture skeleton: `src/app`, `src/core`, `src/domains`, `src/shared`.
- Build core platform abstraction (`src/core/platform`):
  - storage interface and web adapter
  - device identity interface and web adapter
  - camera placeholder interface
  - notifications placeholder interface
- Establish design system integration:
  - semantic tokens (color/type/spacing/motion)
  - base primitives (Button, Input, Card, Badge, Skeleton)
- Define global app shell and route map placeholders.

**Checkpoint**:
- Structure complete.
- No feature logic leakage across domains.
- No direct browser API usage outside platform layer.

## Phase 2: Authentication System
- Implement login + OTP flow screens and navigation.
- Implement session store and token lifecycle policy.
- Build API interceptors:
  - auth header injection
  - one-shot refresh and retry
  - logout fallback
- Implement guards:
  - `AuthGuard`
  - `RoleGuard`
  - `PermissionGuard`
  - base `RuleGuard` infrastructure
- Finalize auth error handling map (generic-safe messages for sensitive failures).

**Checkpoint**:
- Full auth flow works with safe UX states.
- 401 behavior deterministic.
- Security messaging does not leak sensitive identity data.

## Phase 3: Core Banking Foundation
- Build accounts list and account detail.
- Build ledger transaction history and transaction detail shell.
- Build dashboard shell with balance and key action surfaces.
- Integrate KYC status visibility in dashboard and action-entry points.
- Apply account-status gating in action selectors (disable restricted source accounts).

**Checkpoint**:
- User can view account + ledger safely.
- Gating logic prevents invalid action initiation.
- UI states complete (loading/empty/error/restricted).

## Phase 4: Payments Engine
- Implement transfer flow end-to-end:
  - form
  - OTP step
  - confirmation
  - result/reconcile
- Implement QR flow:
  - resolve token
  - OTP
  - execute
  - expired/paid handling
- Implement bill flow:
  - provider list
  - fetch
  - OTP
  - execute
- Implement transaction state machine presentation (`pending`, `processing`, `completed`, `failed`, `reversed`, `flagged`).

**Checkpoint**:
- Idempotency logic enforced for every financial submission.
- Retry path reuses same key for same attempt.
- Duplicate submit is prevented in UI and request layer.

## Phase 5: KYC Full Flow
- Implement full KYC status screen and upload journey.
- Add rejection guidance and re-upload loop.
- Enforce KYC blocking rules in routes and critical action CTA controls.
- Add explicit rule-based copy for pending and rejected states.

**Checkpoint**:
- KYC states are visible and consistent across all payment entry points.
- Financial execution is blocked when KYC not approved.

## Phase 6: Support and Notifications
- Build customer ticket list/detail/reply/close.
- Build notification center with read/unread controls.
- Add polling/invalidation strategy for eventual consistency.
- Enforce ticket reply constraints based on ticket status.

**Checkpoint**:
- Support flow works with proper state constraints.
- Notification state remains consistent across refreshes.

## Phase 7: Staff Dashboard
- Build staff shell and permission-gated navigation.
- Implement:
  - KYC review tools
  - user management
  - risk alerts
  - ledger admin tools
  - support operations
- Enforce mixed role+permission backend reality with layered guards and safe fallbacks.

**Checkpoint**:
- Staff actions are correctly gated at route and action levels.
- Forbidden actions never appear as active controls.

## Phase 8: Hardening and Optimization
- Performance UX:
  - skeleton-first loading
  - route/module lazy loading
  - reduced blocking interactions
- Edge-case hardening:
  - idempotency conflicts
  - stale permission profile
  - KYC mismatch and stale cached states
  - uncertain payment outcomes and reconciliation
- QA hardening:
  - rule-by-rule verification checklist
  - consistency and accessibility checks

**Checkpoint**:
- Production readiness for web phase.
- Migration readiness maintained for later PWA/Capacitor.

---

## 4. Screen-by-Screen Mapping

- **Login Phone**
  - Domain: Auth and Security
  - APIs: auth OTP send/login start
  - Rules: `RULE-001`, `RULE-002`, `RULE-003`
  - Components: Input, Button, Toast
  - States: idle, loading, rate-limited, safe-error

- **OTP Verification**
  - Domain: Auth and Security
  - APIs: OTP verify/login/reset verify
  - Rules: `RULE-002`, `RULE-003`
  - Components: OTP Input, Button, Badge, Toast
  - States: timer, invalid, expired, max-attempt, success

- **Credential Submit**
  - Domain: Auth and Security
  - APIs: login execute
  - Rules: `RULE-004`, `RULE-005`, `RULE-006`
  - Components: Input, Button, Alert Banner
  - States: submitting, blocked, locked, success, auth-failed

- **Dashboard Shell**
  - Domain: Accounts/Ledger/KYC
  - APIs: profile, accounts, KYC status
  - Rules: `RULE-007`, `RULE-010`
  - Components: Balance Card, Badge, Skeleton
  - States: loading, success, restricted-actions

- **KYC Status**
  - Domain: KYC
  - APIs: kyc status
  - Rules: `RULE-007`, `RULE-008`, `RULE-009`
  - Components: Badge, Card, Banner, Button
  - States: not_submitted, pending, approved, rejected

- **KYC Upload**
  - Domain: KYC
  - APIs: kyc upload
  - Rules: `RULE-009`
  - Components: Input (file/document meta), Button, Toast
  - States: selecting, uploading, success, upload-error

- **Accounts List**
  - Domain: Accounts
  - APIs: accounts list
  - Rules: `RULE-010`, `RULE-011`
  - Components: Card, Badge, Skeleton
  - States: loading, empty, success, error

- **Account Detail**
  - Domain: Accounts
  - APIs: account detail
  - Rules: `RULE-010`, `RULE-011`
  - Components: Card, Badge, Transaction summary items
  - States: loading, forbidden, success, error

- **Beneficiary Management**
  - Domain: Accounts
  - APIs: beneficiaries list/create/delete
  - Rules: `RULE-012`
  - Components: Input, Button, Card, Toast
  - States: list-loading, create-success, conflict, validation-error

- **Ledger History**
  - Domain: Ledger and Transactions
  - APIs: ledger list
  - Rules: `RULE-013`, `RULE-014`
  - Components: Transaction item, Badge, Skeleton, Filters
  - States: loading, empty, paginated, error

- **Transaction Detail**
  - Domain: Ledger and Transactions
  - APIs: ledger detail
  - Rules: `RULE-014`, `RULE-015`
  - Components: Receipt layout, Fee breakdown, Badge
  - States: loading, completed, failed, reversed, flagged

- **Transfer Form**
  - Domain: Payments Transfer
  - APIs: transfer OTP request
  - Rules: `RULE-016`, `RULE-017`, `RULE-011`
  - Components: Amount Input, Input, Button, Card
  - States: editable, validation-error, restricted-source

- **Transfer OTP Confirmation**
  - Domain: Payments Transfer
  - APIs: transfer execute
  - Rules: `RULE-016`, `RULE-017`
  - Components: OTP Input, Button, Fee breakdown
  - States: otp-entry, processing, conflict, failure

- **Transfer Result**
  - Domain: Payments Transfer
  - APIs: transfer execute + ledger detail fallback
  - Rules: `RULE-013`, `RULE-014`, `RULE-016`
  - Components: Receipt card, Badge, Action buttons
  - States: success, failed, reconcile-needed

- **QR Resolve and Pay**
  - Domain: Payments QR
  - APIs: qr resolve/otp/pay
  - Rules: `RULE-018`, `RULE-016`
  - Components: Card, Amount Input, OTP Input, Button
  - States: resolving, expired, already-paid, processing, success, failed

- **Bill Payment**
  - Domain: Payments Bills
  - APIs: providers/fetch/otp/pay
  - Rules: `RULE-019`, `RULE-016`
  - Components: Input, Amount Input, Card, Button, Fee breakdown
  - States: providers-loading, fetched, otp-step, processing, success, failure

- **Tickets List and Detail**
  - Domain: Support
  - APIs: tickets list/detail/reply/close
  - Rules: `RULE-025`, `RULE-026`
  - Components: Card, Badge, Input, Button
  - States: open, in_progress, resolved, closed, reply-disabled

- **Notifications Center**
  - Domain: Support and Notifications
  - APIs: notifications list/count/read
  - Rules: `RULE-027`
  - Components: List items, Badge, Button
  - States: loading, unread, all-read, sync-error

- **Staff Shell**
  - Domain: Staff Panel
  - APIs: capability bootstrap + module APIs
  - Rules: `RULE-020`, `RULE-021`, `RULE-022`
  - Components: Sidebar/top nav, cards, badges
  - States: module-allowed, module-denied, partial-access

- **Staff Risk Alerts**
  - Domain: Risk
  - APIs: risk alerts/review/dismiss
  - Rules: `RULE-023`, `RULE-024`
  - Components: Severity badges, cards, modal confirmation, buttons
  - States: open, reviewed, dismissed, actioned, stale-conflict

---

## 5. Rule Enforcement Matrix

### Route-Level Enforcement
- `RULE-001..006`: auth entry and protected route session checks.
- `RULE-007..009`: KYC-sensitive route entry guards for payment execution paths.
- `RULE-020..022`: staff route partition and role/permission gating.

### API-Layer Enforcement
- `RULE-004`: refresh + retry + logout fallback.
- `RULE-016`: idempotency key attach/reuse lifecycle for financial operations.
- `RULE-013..015`: transaction reconciliation fallback after uncertain outcomes.
- `RULE-022`: 403 handling and capability mismatch fallback.

### UI-Component-Level Enforcement
- `RULE-010..012`: disable/hide invalid account and beneficiary actions.
- `RULE-014`: transaction state badges and receipt states.
- `RULE-025..027`: ticket reply state controls and notification state controls.
- `RULE-023..024`: risk action controls disabled in terminal statuses.

---

## 6. UI System Usage Mapping

### Global Components
- Button, Input, Card, Badge, Skeleton Loader, Toast/Snackbar.
- Modal/Bottom Sheet for confirmations and critical decision points.
- OTP Input and Amount Input as high-priority banking primitives.

### Domain-Specific Component Usage
- Auth: OTP Input, secure Input states, warning banner.
- KYC: status badges, warning cards, upload action cards.
- Accounts/Ledger: balance card, transaction row, status badge.
- Payments: amount input, confirmation card, fee breakdown, sticky CTA.
- Support: ticket timeline card, status badge, message composer.
- Risk/Staff: severity badge, review panel card, confirmation modal.

### Critical Token Usage Areas
- Color semantics for financial and risk states must be consistent.
- Typography numeric styles (tabular numerals) mandatory for balances/amounts.
- Spacing/touch targets must follow mobile-first dimensions.
- Motion tokens constrained to subtle 150-250ms transitions.

### Consistency Rules for Banking UI
- Never rely on color only; always include labels/icons for status.
- Every irreversible action must present clear confirmation context.
- Receipt and reference number must be consistently visible post-transaction.
- Error presentation uses safe, non-revealing language for auth/security contexts.

---

## 7. Risk and Edge Case Strategy

## Payment Failure Handling
- Categorize failures: validation, funds, restriction, conflict, unknown.
- Preserve user input where safe.
- Provide deterministic next action: retry, edit, or reconcile.

## Idempotency Conflict Handling
- Same attempt must reuse same key.
- Conflict responses trigger status reconciliation flow.
- Do not auto-generate a new key on same attempt retry.

## KYC Mismatch Handling
- If cached state differs from fresh API, trust latest API.
- Immediately re-evaluate `RuleGuard` and update action availability.
- Show actionable banner and route to KYC flow.

## Permission Mismatch Handling
- On 403 for visible action, downgrade capability locally and refresh permission snapshot.
- Keep action disabled until explicit capability refresh grants access.

## Backend Inconsistency Fallback Rules
- Use feature flags for unstable endpoints.
- Avoid strict dependency on exact error strings.
- Use status class + normalized error type mapping.
- Always keep reconciliation path for uncertain financial outcomes.

---

## 8. Execution Guideline

## Step-by-Step Execution Order
1. Phase 1 foundation and architecture skeleton.
2. Phase 2 authentication and guard framework.
3. Phase 3 core account/ledger dashboard baseline.
4. Phase 4 payments engine and transaction state machine.
5. Phase 5 complete KYC UX and enforcement.
6. Phase 6 support/notifications.
7. Phase 7 staff/risk modules.
8. Phase 8 hardening and optimization.

## Mandatory Review Before Next Phase
- After each phase:
  - Rule coverage review (which `RULE-*` are now enforced).
  - UX consistency review against design system tokens/components.
  - Safety review for financial and permission-sensitive actions.
  - Accessibility and responsive behavior spot-check.

## What Can Be Parallelized
- Design token integration and base component library setup (within Phase 1).
- Domain shell scaffolding for non-dependent modules after guards stabilize.
- Support and notification UI shell work can start while payments hardening is in progress.
- Staff module UI shell can run parallel with backend capability mapping finalization.

## What Must Not Be Implemented Early
- Do not implement payment execution before idempotency and guard framework is complete.
- Do not expose staff actions before permission matrix and 403 fallback handling are complete.
- Do not optimize animations before safety and accessibility baselines are stable.
- Do not add PWA/Capacitor concerns in this execution plan phase.

## Exit Criteria for Master Plan Completion
- All domains mapped with rules, APIs, components, and states.
- All critical flows have checkpointed phase ownership.
- Enforcement matrix is testable at route/API/component levels.
- Risk and inconsistency fallbacks are explicitly documented and actionable.

