## 1) Current system analysis (based on existing code)

### What already exists
- **User-level KYC status on `User`**:
  - `backend/apps/users/models.py` includes `kyc_status` (string choices in `backend/apps/users/constants.py::KycStatus`)
  - Status values currently: `NOT_SUBMITTED`, `PENDING`, `APPROVED`, `REJECTED`
- **Document model**:
  - `backend/apps/kyc/models.py::KycDocument`
    - fields: `user`, `document_type`, `file`, `status`, `reviewed_by`, `reviewed_at`, `rejection_reason`, `notes`
    - document statuses: pending/approved/rejected (see `backend/apps/kyc/constants.py`)
- **Customer KYC APIs**:
  - `GET /api/kyc/status/` → returns current user `kyc_status` + documents list (`backend/apps/kyc/views.py::kyc_status`)
  - `POST /api/kyc/upload/` → uploads a document; sets user `kyc_status` to `PENDING` (unless already `APPROVED`)
- **Staff KYC APIs** (permission: `review_kyc`):
  - `GET /api/staff/kyc/pending/` → queue (users where `kyc_status=PENDING`)
  - `GET /api/staff/kyc/users/{user_id}/documents/` → list documents
  - `POST /api/staff/kyc/users/{user_id}/approve/` → sets user `kyc_status=APPROVED`
  - `POST /api/staff/kyc/users/{user_id}/reject/` → sets user `kyc_status=REJECTED`
  - `POST /api/staff/kyc/documents/{doc_id}/approve/` / `/reject/`
- **Financial enforcement** (defence-in-depth):
  - `backend/apps/ledger/services.py::_assert_kyc_approved` blocks all monetary operations unless `User.kyc_status == APPROVED`
  - This means **even if someone bypasses a view**, the ledger write-path still refuses.

### What is missing vs real banking KYC
- **KYC is document-only today**: there is no structured “KYC profile” (personal info + address + document metadata + audit trail of decisions).
- **No “needs update / expired / resubmission” state** beyond `REJECTED`.
- **No review assignment / SLA**:
  - who is assigned to review, queue ordering, timestamps for escalation.
- **No strong linkage between “document review” and “user approval”**:
  - staff can approve user-level KYC even if documents are still pending/rejected.
- **No immutable decision history**:
  - `KycDocument` has review fields, but user-level approve/reject doesn’t keep a structured audit record.
- **No fraud/risk scoring integration for KYC**:
  - you have a risk app for alerts, but KYC risk isn’t explicitly scored.
- **No constraints on uploads**:
  - file type/size, per-type limits, anti-malware scanning, duplicate submission prevention, etc.
- **No “KYC gates by product”**:
  - real banks allow partial accounts (view-only / low limits) before full KYC; your system is currently “no KYC → no transactions”.


## 2) Real-world banking KYC flow (step-by-step)

### Stage A: Onboarding (account creation)
- Customer identity is created (phone/email, name).
- Phone is verified (OTP).
- Account is opened in a restricted state (often “limited wallet” or “no outgoing transfers”).

### Stage B: Identity capture (customer-provided data)
- Customer submits:
  - legal name, DOB, nationality
  - national ID / passport number
  - address + proof (utility bill, bank statement)
  - sometimes occupation/source-of-funds
  - optional selfie / liveness check
- Data is validated (format checks, age checks, consistency).

### Stage C: Document verification
- Automated checks (optional in real systems):
  - OCR extraction and match (name/ID number)
  - tamper detection
  - selfie match / liveness
- Manual review queue:
  - staff verifies document authenticity, compares data, requests resubmission if unclear.

### Stage D: Approval / rejection
- Staff decision:
  - Approved → KYC verified → enable full product access (transactions, limits)
  - Rejected → restrict access; require resubmission; store reason codes
  - Needs update → allow resubmission without “permanent rejection”

### Stage E: Risk scoring (optional but common)
- KYC risk score considers:
  - device and geolocation anomalies
  - velocity (many accounts with similar data)
  - watchlist checks (sanctions/PEP) in real systems
  - suspicious document patterns
- Risk outcomes:
  - auto-approve low risk
  - manual review medium risk
  - block/high friction for high risk


## 3) Proposed KYC architecture for your project

### A) KYC stages (recommended)
Keep your existing statuses but extend to support real bank behavior.

Recommended `User.kyc_status` (user-level):
- `NOT_SUBMITTED`
- `PENDING_REVIEW`
- `APPROVED`
- `REJECTED`
- `NEEDS_UPDATE`

Document-level (`KycDocument.status`):
- `PENDING`
- `APPROVED`
- `REJECTED`

Mapping rule:
- If any required doc is missing → user-level cannot be `APPROVED`.
- If user uploaded something and review not finished → `PENDING_REVIEW`.
- If documents were rejected but resubmission allowed → `NEEDS_UPDATE` (better than hard `REJECTED`).

### B) Required data (minimum viable bank-like KYC)

**KYC profile fields (structured)**
- legal_full_name (string)
- date_of_birth (date)
- nationality (string)
- gender (optional)
- id_type (enum: NATIONAL_ID, PASSPORT)
- id_number (string)
- id_expiry_date (optional)
- address_line1, address_city, address_country
- postal_code (optional)
- source_of_funds (optional for final year scope; recommended)
- occupation (optional)

**Documents**
- National ID / Passport (required)
- Proof of address (optional but recommended)
- Selfie (future)

**Already covered**
- phone verification (OTP-first onboarding)

### C) Workflow (who does what)

Customer:
- completes OTP-first onboarding
- submits KYC profile fields
- uploads documents

Staff (KYC Reviewer):
- reviews documents
- approves/rejects KYC with reasons
- can request update/resubmission

After approval:
- customer gains financial access (already enforced by ledger service)


## 4) Roles & responsibilities (very important)

### Customer
- **Can**:
  - submit KYC profile
  - upload documents
  - view their own KYC status + rejection reasons
  - resubmit when status is `NEEDS_UPDATE`/`REJECTED` (depending on policy)
- **Cannot**:
  - approve/reject
  - see other users’ KYC

### Teller
Recommended for your project:
- **Can**:
  - register customer + open account (already implemented)
  - *optionally* help upload documents for customer (branch-assisted flow) BUT still cannot approve
- **Cannot**:
  - approve/reject KYC (separation of duties)

### Admin / KYC Reviewer
- **Can**:
  - approve/reject user KYC
  - approve/reject individual documents
  - request resubmission (`NEEDS_UPDATE`)
  - override decisions (tracked by audit logs)

### Additional role (recommended)
Add a dedicated role code (optional but realistic):
- `KYC_OFFICER` (or reuse existing `RISK_OFFICER` if you want fewer roles)

Permissions:
- `review_kyc` (already exists) → grant to Admin + KYC Officer


## 5) Backend design

### Database design (recommended additions)

#### 1) Add a structured KYC profile model
Create `KycProfile` (1:1 with User):
- `user` (OneToOne)
- `legal_full_name`
- `date_of_birth`
- `nationality`
- `id_type`, `id_number`, `id_expiry_date`
- `address_line1`, `address_city`, `address_country`, `postal_code`
- `submitted_at`
- `last_updated_at`

Reason: do not overload `User` with dozens of KYC fields; keeps domain clean.

#### 2) Add a user-level KYC decision/audit history table
Create `KycDecision` (append-only):
- `user`
- `decided_by` (staff user)
- `decision` (`APPROVED`, `REJECTED`, `NEEDS_UPDATE`)
- `reason_code` (enum/string)
- `reason_text` (free text)
- `created_at`

Reason: audit trail + explainability.

#### 3) Tighten `KycDocument`
Keep as-is but add (optional):
- `checksum_sha256` (dedupe)
- `mime_type`, `file_size`
- `document_number_extracted` (future OCR)

### Business rules (service-layer)
Enforce these in `apps/kyc/services.py`:
- `submit_kyc_profile()` sets `User.kyc_status = PENDING_REVIEW` unless already `APPROVED`.
- `upload_kyc_document()` sets user `PENDING_REVIEW` unless already `APPROVED`.
- `approve_user_kyc()` requires:
  - profile exists and is complete
  - required documents exist and are `APPROVED`
  - then set `User.kyc_status = APPROVED`
- `reject_user_kyc()` sets `REJECTED` or `NEEDS_UPDATE` with reason code/text.


## 6) API design

### Customer endpoints (`/api/kyc/`)
- `GET  /api/kyc/status/`
  - returns: `kyc_status`, `profile` (if any), `documents`, `rejection_reasons` (latest)
- `POST /api/kyc/profile/submit/`
  - body: KYC profile fields
  - result: `kyc_status=PENDING_REVIEW`
- `PATCH /api/kyc/profile/`
  - allow edits only when status is `NOT_SUBMITTED`, `NEEDS_UPDATE`, `REJECTED` (policy)
- `POST /api/kyc/upload/`
  - existing; keep multipart upload
- `DELETE /api/kyc/documents/{id}/`
  - allow only if doc is `PENDING` and user is resubmitting (optional)

### Staff endpoints (`/api/staff/kyc/`) (permission: `review_kyc`)
- `GET  /api/staff/kyc/pending/`
  - include: profile completeness, doc counts, age in queue
- `GET  /api/staff/kyc/users/{user_id}/`
  - user summary + profile + docs + decision history
- `POST /api/staff/kyc/users/{user_id}/approve/`
  - server validates required docs/profile completeness
- `POST /api/staff/kyc/users/{user_id}/reject/`
  - body: `{ reason_code, reason_text }`
- `POST /api/staff/kyc/users/{user_id}/needs-update/`
  - body: `{ reason_code, reason_text }`
- `POST /api/staff/kyc/documents/{doc_id}/approve/`
- `POST /api/staff/kyc/documents/{doc_id}/reject/`


## 7) Security & validation rules

### Validation rules (server-side)
- **Phone**:
  - already normalized and verified by OTP-first onboarding
- **KYC profile fields**:
  - required fields must be present before allowing final approval
  - DOB: enforce minimum age (e.g. 18)
  - ID number format checks (basic regex)
- **Documents**:
  - file type whitelist (jpg/png/pdf)
  - size limits
  - rate limit uploads per day/user
  - checksum-based dedupe (optional)

### Prevent bypassing KYC
You already have the strongest control:
- `apps.ledger.services::_assert_kyc_approved` blocks balance mutations unless `kyc_status=APPROVED`

Extend to also guard other sensitive features if needed:
- bill pay, transfer, qr pay already route through ledger services; they’re covered.

### Fraud prevention (FYP-appropriate)
- throttle document uploads
- throttle staff approvals (optional)
- log every decision (`KycDecision`)
- store rejection reason codes for analytics and user guidance


## 8) Final recommended flow (integrated with your current system)

### Recommended lifecycle (customer)
1. Teller registers customer (branch) → customer account exists, **first_login_completed=false**, **kyc_status=NOT_SUBMITTED**
2. Customer completes OTP-first onboarding → sets password + PIN
3. Customer submits KYC profile + uploads documents → status becomes `PENDING_REVIEW`
4. Staff reviews documents + profile:
   - approve docs → approve user KYC → status `APPROVED`
   - reject → status `NEEDS_UPDATE` (preferred) or `REJECTED` with reasons
5. Transactions:
   - blocked until `APPROVED` (already enforced in ledger)
   - after approval, require PIN for customer payments (Transfer/QR/Bills)

### Recommended lifecycle (staff)
1. KYC queue shows PENDING_REVIEW users with completeness signals
2. Staff reviews docs, requests resubmission if needed
3. Staff approves entire KYC only when requirements are satisfied
4. Every action creates audit trail records (document review fields + `KycDecision`)

