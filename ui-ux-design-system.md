# SafeT UI/UX Design System

## Purpose

This document defines the UI/UX design system for the SafeT banking web application (mobile-first), with future compatibility for PWA and mobile shell migration.  
It is design-spec only (no implementation code).

Design principles:
- Trustworthy
- Minimal
- Fast
- Premium
- Secure by default

---

## 1) Design Foundation

## 1.1 Color System (Semantic)

### Core Palette (Light Mode)

- **Primary (Trust)**: `#0F4C81` (deep financial blue)
- **Primary Hover**: `#0C3E69`
- **Primary Soft Background**: `#EAF3FB`

- **Secondary (Supportive Accent)**: `#2E6B5A` (teal-slate)
- **Secondary Soft Background**: `#EAF5F1`

- **Success**: `#1E8E5A`
- **Success Background**: `#EAF7F0`

- **Warning**: `#B7791F`
- **Warning Background**: `#FFF7E8`

- **Danger**: `#C53030`
- **Danger Background**: `#FDECEC`

- **Info**: `#2563EB`
- **Info Background**: `#EEF4FF`

### Neutral / Structure

- **Background Base**: `#F7F9FC`
- **Surface Primary**: `#FFFFFF`
- **Surface Secondary**: `#F2F5FA`
- **Border Default**: `#DCE3EE`
- **Border Strong**: `#C2CEDD`
- **Divider**: `#E7EDF5`

### Text Hierarchy

- **Text Primary**: `#0F172A`
- **Text Secondary**: `#334155`
- **Text Tertiary**: `#64748B`
- **Text Disabled**: `#94A3B8`
- **Text On Primary**: `#FFFFFF`
- **Link**: `#1D4ED8`
- **Link Hover**: `#1E40AF`

### Status Mappings (Must Be Consistent)

- Transaction credit: Success color family
- Transaction debit: Danger color family
- Pending/processing: Warning or info family
- Reversed: Tertiary neutral with warning accent
- Blocked/locked: Danger family

### Accessibility Rules

- Minimum contrast: WCAG AA for all text and critical controls.
- Body text must always have AA contrast against background.
- Never rely on color alone for status (always pair with icon/label).
- Disabled states must remain legible and distinguishable from active.

### Future Dark Mode Note (Optional Later)

- Keep semantic token names stable now (`color.text.primary`, `color.bg.surface`, etc.).
- Add dark token values later without changing component API.

---

## 1.2 Typography System

### Font Families

- **Primary UI Font**: `Inter` (or `Manrope` fallback option)
- **Numeric Font (Balances/Amounts)**: same family, but use tabular numerals (`font-variant-numeric: tabular-nums`) for alignment.

Rationale:
- Modern and clear at small sizes.
- Excellent readability for financial data.

### Type Scale

- **H1**: 32px / 40px / 700
- **H2**: 28px / 36px / 700
- **H3**: 24px / 32px / 600
- **H4**: 20px / 28px / 600
- **H5**: 18px / 26px / 600
- **H6**: 16px / 24px / 600

- **Body Large**: 16px / 24px / 400
- **Body**: 14px / 22px / 400
- **Body Small**: 13px / 20px / 400

- **Caption**: 12px / 18px / 500
- **Helper/Error Text**: 12px / 18px / 500
- **Overline/Label**: 11px / 16px / 600, uppercase optional

### Numeric Display Styles

- **Balance XL**: 32px / 40px / 700 (tabular numerals)
- **Balance L**: 24px / 32px / 700
- **Amount M**: 18px / 26px / 600
- Currency symbol slightly reduced (85-90%) to improve readability.

### Typography Rules

- Avoid light font weights for transactional data.
- Use sentence case for readability (all-caps only for micro labels).
- Keep line length narrow on mobile for critical text.

---

## 1.3 Spacing and Layout System

### Spacing Grid

Use **8px base grid** with 4px support:
- 4, 8, 12, 16, 20, 24, 32, 40, 48, 64

### Core Spacing Rules

- Screen horizontal padding:
  - Mobile: 16px
  - Tablet+: 24px
- Card padding:
  - Default: 16px
  - Dense list card: 12px
- Button padding:
  - Horizontal: 16-20px
  - Vertical: 10-12px
- Form field vertical gap: 12-16px
- Section gap: 24px minimum

### Mobile-First Layout Constraints

- Content max width:
  - Mobile-first full width
  - Optional readable container max ~720px on larger screens
- Avoid fixed pixel widths for cards/forms unless for max-width constraints.
- Use fluid grid/flex layouts; preserve one-column flow for critical steps.

---

## 2) Component Design System

## 2.1 Button

Variants:
- Primary
- Secondary
- Danger
- Ghost/Text (optional utility)

States:
- Default
- Hover
- Focus-visible
- Pressed
- Disabled
- Loading

UX rules:
- Minimum height: 44px
- Primary action appears once per section/screen.
- Loading state must preserve width and show progress indicator.
- Disabled must clearly indicate unavailable action and remain accessible.

---

## 2.2 Input

Types:
- Text
- Phone
- Password/PIN
- Numeric/Amount

States:
- Default
- Focused
- Filled
- Error
- Disabled
- Read-only

UX rules:
- Label always visible (not placeholder-only).
- Error text directly below field.
- Keep helper and error messages concise and actionable.

---

## 2.3 Card (Banking Card Pattern)

Types:
- Standard info card
- Account balance card
- Transaction card/list row
- Warning status card

States:
- Normal
- Interactive hover (web)
- Selected
- Disabled

UX rules:
- Use elevation sparingly; rely on border + subtle shadow.
- Key financial numbers must be high contrast and tabular.

---

## 2.4 Modal and Bottom Sheet

Usage:
- Modal for confirmation/critical decisions on larger viewports.
- Bottom sheet for mobile contextual actions.

States:
- Open
- Closing
- Blocking action
- Error in modal context

UX rules:
- Never stack multiple modals.
- Financial confirmations must include summary + fee + destination/source.
- Primary action right-aligned (desktop) or full-width sticky (mobile).

---

## 2.5 Toast / Snackbar

Types:
- Success
- Error
- Warning
- Info

UX rules:
- Auto-dismiss non-critical notifications.
- Critical failures require persistent inline error on affected view.
- Do not use toast as sole channel for irreversible action outcomes.

---

## 2.6 Badge (Status Indicators)

Use for:
- KYC status
- Account status
- Transaction status
- Risk severity

Rules:
- Pair badge text with semantic color and optional icon.
- Keep labels short and exact backend-aligned states.

---

## 2.7 Skeleton Loader

Rules:
- Use skeletons for lists/cards/forms where content structure is known.
- Prefer skeleton over spinner for loads >300ms.
- Keep skeleton layout close to final shape to reduce visual shift.

---

## 2.8 OTP Input (Segmented)

Design:
- 6 segmented cells by default.

Behavior rules:
- Auto-advance on digit input.
- Backspace navigates backward.
- Paste support for full OTP.
- Show timer and resend states clearly.
- Masking optional based on security policy.

---

## 2.9 Amount Input (Financial)

Behavior:
- Numeric keypad preference on mobile.
- Supports decimal precision to 2 places.
- Sanitizes invalid characters.
- Real-time formatting without disrupting typing.

UX rules:
- Show currency context near input.
- Show available balance nearby when applicable.
- Show fee preview before final confirmation.

---

## 3) Mobile-First UX Rules

- Minimum touch target: **44x44px** (prefer 48x48px for major actions).
- Keep primary actions in thumb-friendly lower zone on mobile.
- Use sticky bottom action bar for high-importance flows (transfer confirm, OTP submit).
- Avoid edge-to-edge tap targets without safe padding.
- Keep form submit CTA visible without requiring excessive scroll.
- Keyboard-aware form behavior:
  - Inputs remain visible when keyboard opens.
  - Sticky CTA must not overlap focused fields.

---

## 4) Animation System

## Philosophy

- Subtle, fast, purposeful, non-blocking.
- Motion should clarify state change, never distract.

Allowed animations:
- Fade in/out
- Slide up/down (sheet, toast)
- Tap scale feedback (micro interaction)

Duration standards:
- Fast: 150ms
- Standard: 200ms
- Slow max: 250ms

Rules:
- Use standard easing tokens consistently.
- No long decorative animations on financial confirmation paths.
- Respect reduced-motion user preferences.

---

## 5) Financial UI Patterns

## 5.1 Balance Display Card

- Prominent balance typography with tabular numerals.
- Show account type, currency, status.
- Secondary row for available vs ledger balance when needed.

## 5.2 Transaction Item

- Left: type + counterparty/context
- Right: signed amount and status
- Credit/debit visually distinct by semantic tokens, not just color.

## 5.3 Confirmation Screen

Required sections:
- Source
- Destination
- Amount
- Fee
- Total impact
- OTP step indicator (if applicable)

## 5.4 Fee Breakdown

- Always show principal + fee + total.
- Include subtle note if fee is rule-based and may vary.

## 5.5 Receipt Screen (Success / Failure)

- Receipt header with clear status.
- Reference number prominently visible.
- Action row: copy reference, share, back to dashboard/history.

## 5.6 Risk / Blocked Pattern

- Distinct warning panel with cause summary.
- Clear next actions (contact support, wait for review, upload KYC).
- Disable prohibited actions with explanation text.

---

## 6) Trust and Security UX Patterns

## Locked Account State

- Full-width high-priority alert banner.
- Avoid technical details; provide safe next step.
- Disable transaction actions globally while locked.

## KYC Pending / Rejected

- Persistent contextual banner in dashboard and payment entry screens.
- Pending: informational with timeline expectation.
- Rejected: warning with direct re-upload CTA.

## Session Expired Pattern

- Clear interruption modal/banner.
- Preserve unsent form data when safe.
- Redirect to re-auth flow with reason label.

## Warning / Error Presentation

- Inline field errors for form input issues.
- Section-level alerts for business rule failures.
- Global banner only for session/security-critical states.

## Non-Revealing Error Messaging

- Do not reveal whether account/phone exists.
- Use neutral phrasing for auth failures.
- Put actionable guidance without exposing backend internals.

---

## 7) Performance UX Rules

- Prefer skeletons for content loading.
- Use optimistic micro-feedback (button press response under 100ms).
- Disable repeated submit during in-flight calls.
- Keep UI interactive during background refresh where safe.
- Lazy-load heavy routes/modules and show route skeleton.
- Prevent full-screen blocking loaders except for security transitions.
- Maintain layout stability (minimize cumulative layout shift).

---

## Token Naming Convention (For Future Implementation)

Use semantic token names:
- `color.bg.base`, `color.bg.surface`, `color.text.primary`
- `color.state.success`, `color.state.warning`, `color.state.danger`
- `space.1` ... `space.8`
- `radius.sm`, `radius.md`, `radius.lg`
- `shadow.sm`, `shadow.md`
- `motion.fast`, `motion.standard`

This enables future theming and platform expansion without changing component contracts.

---

## Governance and Usage Rules

- New components must map to existing semantic tokens before introducing new ones.
- All transaction-related screens must pass contrast and readability checks.
- Any deviation from this system requires design review approval.
- Keep status labels aligned with backend enum values to avoid ambiguity.

---

## Version

- Design System Version: `v1.0-web-foundation`
- Theme Scope: `Light mode production; dark mode optional future`
- Platform Scope: `Web now, PWA/Capacitor-ready architecture`
