# SafeT Database Schema

## Scope
- Database target: Django ORM + MySQL
- Ignore `Full System Features Report.docx`
- Login identifier: phone number only
- No biometric or fingerprint data is stored
- All money movement goes through the ledger transaction system

## Global Statuses

### User status
- `PENDING_VERIFICATION`
- `ACTIVE`
- `REJECTED`
- `BLOCKED`

### Account status
- `ACTIVE`
- `FROZEN`
- `BLOCKED`
- `CLOSED`

### Transaction type
- `TRANSFER`
- `DEPOSIT`
- `WITHDRAWAL`
- `QR_PAYMENT`
- `BILL_PAYMENT`

### Transaction status
- `PENDING`
- `PROCESSING`
- `COMPLETED`
- `FAILED`
- `REVERSED`
- `CANCELLED`

## Hybrid Registration Rule
1. Customer self-registers with phone number.
2. OTP verifies the phone number.
3. Customer sets a PIN.
4. System creates `User.status = PENDING_VERIFICATION`.
5. Pending users can log in but cannot create monetary transactions.
6. `Teller` or `Admin` approves or rejects the user.
7. Approval fields: `status`, `approved_by`, `approved_at`, `rejection_reason`.

## App Boundaries
- `users`: `Role`, `Permission`, `RolePermission`, `User`, `PhoneNumber`
- `kyc`: `KycDocument`
- `accounts`: `Currency`, `Account`, `AccountRestriction`, `Beneficiary`
- `ledger`: `Transaction`, `TransactionEntry`, `TransactionHistory`, `FeeRule`
- `payments`: `MerchantProfile`, `QRPayment`, `BillProvider`, `BillPayment`
- `security`: `OTPRequest`, `LoginLog`, `UserDevice`, `AccountLockEvent`, `PasswordResetAudit`
- `support`: `SupportTicket`, `Notification`
- `risk`: `FraudAlert`, `FraudDecision`

## Core Identity and Access Models

### Role
- Fields:
  - `id: BigAutoField`
  - `code: CharField(50, unique=True)`
  - `name: CharField(100, unique=True)`
  - `description: TextField(blank=True)`
  - `is_staff_role: BooleanField(default=False)`
  - `is_system_role: BooleanField(default=False)`
  - `created_at`, `updated_at`
- Relationships:
  - one `Role` to many `User`
  - one `Role` to many `RolePermission`
- Constraints:
  - unique `code`
  - seeded roles should be protected from deletion
- Indexes:
  - `code`
  - `is_staff_role`

### Permission
- Fields:
  - `id`
  - `code: CharField(100, unique=True)`
  - `name: CharField(150)`
  - `module: CharField(50)`
  - `description: TextField(blank=True)`
  - `created_at`
- Relationships:
  - one `Permission` to many `RolePermission`
- Constraints:
  - unique `code`
- Indexes:
  - composite `(module, code)`

### RolePermission
- Fields:
  - `id`
  - `role: FK -> Role`
  - `permission: FK -> Permission`
  - `granted_by: FK -> User, null=True`
  - `created_at`
- Relationships:
  - many-to-one to `Role`
  - many-to-one to `Permission`
- Constraints:
  - unique `(role, permission)`
- Indexes:
  - unique composite `(role_id, permission_id)`

### User
- Fields:
  - `id`
  - `role: FK -> Role`
  - `full_name: CharField(255)`
  - `phone_number: CharField(20, unique=True)`
  - `phone_number_normalized: CharField(20, unique=True)`
  - `password_hash: CharField(255)`
  - `pin_hash: CharField(255)`
  - `status: CharField(30)`
  - `kyc_status: CharField(30, default='PENDING')`
  - `is_phone_verified: BooleanField(default=False)`
  - `last_login_at: DateTimeField(null=True)`
  - `approved_by: FK -> User, null=True`
  - `approved_at: DateTimeField(null=True)`
  - `rejection_reason: TextField(blank=True)`
  - `blocked_reason: TextField(blank=True)`
  - `created_at`, `updated_at`
- Relationships:
  - one `User` to many `Account`, `OTPRequest`, `LoginLog`, `UserDevice`, `SupportTicket`, `Notification`, `KycDocument`, `PhoneNumber`
  - one merchant `User` to one `MerchantProfile`
- Constraints:
  - phone is the only login identifier
  - `approved_by` must be a `Teller` or `Admin` in service-layer validation
  - rejected users should have `rejection_reason`
  - pending users may log in but cannot transact
- Indexes:
  - unique `phone_number_normalized`
  - composite `(role_id, status)`
  - `kyc_status`
  - `created_at`

### PhoneNumber
- Fields:
  - `id`
  - `user: FK -> User`
  - `phone_number: CharField(20, unique=True)`
  - `phone_number_normalized: CharField(20, unique=True)`
  - `label: CharField(30, default='SECONDARY')`
  - `is_verified: BooleanField(default=False)`
  - `is_active: BooleanField(default=True)`
  - `created_at`
- Relationships:
  - many-to-one to `User`
- Constraints:
  - primary login number stays on `User.phone_number`
- Indexes:
  - unique normalized number
  - composite `(user_id, is_active)`

### KycDocument
- Fields:
  - `id`
  - `user: FK -> User`
  - `document_type: CharField(50)`
  - `document_number: CharField(100)`
  - `file_path: CharField(500)`
  - `status: CharField(30, default='PENDING')`
  - `reviewed_by: FK -> User, null=True`
  - `reviewed_at: DateTimeField(null=True)`
  - `rejection_reason: TextField(blank=True)`
  - `expires_at: DateTimeField(null=True)`
  - `created_at`, `updated_at`
- Relationships:
  - many-to-one to `User`
  - many-to-one to reviewer `User`
- Constraints:
  - unique `(document_type, document_number)`
- Indexes:
  - composite `(user_id, status)`
  - composite `(document_type, document_number)`
  - `expires_at`

## Accounts and Ledger Models

### Currency
- Fields:
  - `code: CharField(3, primary_key=True)`
  - `name: CharField(50)`
  - `symbol: CharField(10, blank=True)`
  - `decimal_places: PositiveSmallIntegerField(default=2)`
  - `is_active: BooleanField(default=True)`
  - `created_at`
- Relationships:
  - one `Currency` to many `Account`, `Transaction`, `FeeRule`
- Constraints:
  - ISO 4217 code policy
- Indexes:
  - `is_active`

### Account
- Fields:
  - `id`
  - `user: FK -> User`
  - `currency: FK -> Currency`
  - `account_number: CharField(34, unique=True)`
  - `account_name: CharField(255)`
  - `status: CharField(20)`
  - `available_balance: DecimalField(18,2)`
  - `ledger_balance: DecimalField(18,2)`
  - `blocked_amount: DecimalField(18,2, default=0)`
  - `opened_at`
  - `closed_at: DateTimeField(null=True)`
  - `closed_reason: TextField(blank=True)`
  - `created_by: FK -> User, null=True`
  - `updated_at`
- Relationships:
  - many-to-one to `User`
  - many-to-one to `Currency`
  - one `Account` to many `TransactionEntry`, `AccountRestriction`, `SupportTicket`
- Constraints:
  - unique `account_number`
  - accounts in `FROZEN`, `BLOCKED`, or `CLOSED` cannot originate customer transactions
  - `available_balance <= ledger_balance`
- Indexes:
  - unique `account_number`
  - composite `(user_id, status)`
  - composite `(currency_id, status)`

### Beneficiary
- Fields:
  - `id`
  - `owner: FK -> User`
  - `destination_account: FK -> Account`
  - `nickname: CharField(100)`
  - `is_active: BooleanField(default=True)`
  - `verified_at: DateTimeField(null=True)`
  - `created_at`
- Relationships:
  - many-to-one to owner `User`
  - many-to-one to destination `Account`
- Constraints:
  - unique `(owner, destination_account)`
- Indexes:
  - unique composite `(owner_id, destination_account_id)`
  - composite `(owner_id, is_active)`

### AccountRestriction
- Fields:
  - `id`
  - `account: FK -> Account`
  - `restriction_type: CharField(20)`
  - `reason: TextField()`
  - `source: CharField(30)`
  - `applied_by: FK -> User, null=True`
  - `released_by: FK -> User, null=True`
  - `starts_at: DateTimeField()`
  - `ends_at: DateTimeField(null=True)`
  - `is_active: BooleanField(default=True)`
  - `metadata_json: JSONField(default=dict, blank=True)`
  - `created_at`
- Relationships:
  - many-to-one to `Account`
- Constraints:
  - only one active freeze or block of the same type per account
  - latest active restriction must align with `Account.status`
- Indexes:
  - composite `(account_id, is_active)`
  - composite `(restriction_type, is_active)`
  - `starts_at`

### Transaction
- Fields:
  - `id`
  - `reference_number: CharField(40, unique=True)`
  - `transaction_type: CharField(20)`
  - `status: CharField(20)`
  - `currency: FK -> Currency`
  - `amount: DecimalField(18,2)`
  - `description: CharField(255, blank=True)`
  - `channel: CharField(30)`
  - `initiated_by: FK -> User, null=True`
  - `customer: FK -> User, null=True`
  - `requires_otp: BooleanField(default=False)`
  - `otp_verified_at: DateTimeField(null=True)`
  - `risk_score: DecimalField(5,2, null=True)`
  - `parent_transaction: FK -> Transaction, null=True`
  - `idempotency_key: CharField(64, unique=True, null=True)`
  - `occurred_at`
  - `completed_at: DateTimeField(null=True)`
  - `reversed_at: DateTimeField(null=True)`
  - `failure_code: CharField(50, blank=True)`
  - `failure_reason: TextField(blank=True)`
  - `metadata_json: JSONField(default=dict, blank=True)`
- Relationships:
  - one `Transaction` to many `TransactionEntry`, `FraudAlert`, `Notification`
  - one optional `Transaction` to one `QRPayment`
  - one optional `Transaction` to one `BillPayment`
- Constraints:
  - `amount > 0`
  - every completed transaction must have balanced entries
  - no external money movement may bypass this table
  - use `parent_transaction` for reversals instead of mutating old rows
- Indexes:
  - unique `reference_number`
  - composite `(transaction_type, status)`
  - composite `(customer_id, occurred_at)`
  - composite `(initiated_by_id, occurred_at)`
  - `completed_at`
  - `idempotency_key`

### TransactionEntry
- Fields:
  - `id`
  - `transaction: FK -> Transaction`
  - `account: FK -> Account`
  - `entry_type: CharField(10)` 
  - `amount: DecimalField(18,2)`
  - `sequence_no: PositiveSmallIntegerField()`
  - `created_at`
- Relationships:
  - many-to-one to `Transaction`
  - many-to-one to `Account`
- Constraints:
  - entry types: `DEBIT`, `CREDIT`, `FEE`, `HOLD`, `RELEASE`
  - unique `(transaction, sequence_no)`
  - posted transactions must balance debit and credit totals
- Indexes:
  - composite `(transaction_id, sequence_no)`
  - composite `(account_id, created_at)`
  - composite `(entry_type, created_at)`

### TransactionHistory
- Fields:
  - `id`
  - `transaction: OneToOne -> Transaction`
  - `reference_number: CharField(40)`
  - `transaction_type: CharField(20)`
  - `status: CharField(20)`
  - `currency_code: CharField(3)`
  - `amount: DecimalField(18,2)`
  - `payload_json: JSONField()`
  - `archived_at`
- Relationships:
  - one-to-one with `Transaction`
- Constraints:
  - one archive snapshot per transaction
- Indexes:
  - unique `transaction_id`
  - `reference_number`
  - `archived_at`

### FeeRule
- Fields:
  - `id`
  - `name: CharField(100)`
  - `transaction_type: CharField(20)`
  - `currency: FK -> Currency`
  - `min_amount: DecimalField(18,2, default=0)`
  - `max_amount: DecimalField(18,2, null=True)`
  - `fixed_fee: DecimalField(18,2, default=0)`
  - `percentage_fee: DecimalField(7,4, default=0)`
  - `priority: PositiveSmallIntegerField(default=100)`
  - `is_active: BooleanField(default=True)`
  - `effective_from: DateTimeField()`
  - `effective_to: DateTimeField(null=True)`
  - `created_at`
- Relationships:
  - many-to-one to `Currency`
- Constraints:
  - no overlapping active rules for same operation window and priority
- Indexes:
  - composite `(transaction_type, currency_id, is_active)`
  - composite `(effective_from, effective_to)`

## Payments and Security Models

### MerchantProfile
- Fields:
  - `id`
  - `user: OneToOne -> User`
  - `settlement_account: FK -> Account`
  - `business_name: CharField(255)`
  - `business_type: CharField(100)`
  - `registration_number: CharField(100, unique=True)`
  - `tax_number: CharField(100, blank=True)`
  - `contact_phone: CharField(20)`
  - `address: TextField(blank=True)`
  - `status: CharField(30, default='ACTIVE')`
  - `created_at`, `updated_at`
- Relationships:
  - one-to-one with merchant `User`
  - one-to-many to `QRPayment`
- Constraints:
  - related user role must be `MERCHANT_CUSTOMER`
- Indexes:
  - `registration_number`
  - `status`
  - `business_name`

### QRPayment
- Fields:
  - `id`
  - `transaction: OneToOne -> Transaction`
  - `merchant_profile: FK -> MerchantProfile`
  - `merchant_account: FK -> Account`
  - `payer_account: FK -> Account`
  - `qr_token: CharField(128, unique=True)`
  - `qr_payload_hash: CharField(128)`
  - `amount_mode: CharField(20)`
  - `display_amount: DecimalField(18,2, null=True)`
  - `scanned_at: DateTimeField(null=True)`
  - `created_at`
- Relationships:
  - one-to-one with `Transaction`
  - many-to-one to `MerchantProfile`
- Constraints:
  - linked transaction must be `QR_PAYMENT`
- Indexes:
  - unique `qr_token`
  - composite `(merchant_profile_id, created_at)`
  - composite `(merchant_account_id, created_at)`

### BillProvider
- Fields:
  - `id`
  - `code: CharField(50, unique=True)`
  - `name: CharField(255)`
  - `service_type: CharField(50)`
  - `provider_account: FK -> Account`
  - `is_active: BooleanField(default=True)`
  - `created_at`
- Relationships:
  - one `BillProvider` to many `BillPayment`
- Constraints:
  - unique `code`
- Indexes:
  - `code`
  - composite `(service_type, is_active)`

### BillPayment
- Fields:
  - `id`
  - `transaction: OneToOne -> Transaction`
  - `bill_provider: FK -> BillProvider`
  - `payer_account: FK -> Account`
  - `service_number: CharField(100)`
  - `bill_reference: CharField(100)`
  - `biller_amount: DecimalField(18,2)`
  - `fee_amount: DecimalField(18,2, default=0)`
  - `fetched_at: DateTimeField(null=True)`
  - `paid_at: DateTimeField(null=True)`
  - `created_at`
- Relationships:
  - one-to-one with `Transaction`
  - many-to-one to `BillProvider`
- Constraints:
  - linked transaction must be `BILL_PAYMENT`
- Indexes:
  - composite `(bill_provider_id, service_number)`
  - composite `(payer_account_id, created_at)`
  - `bill_reference`

### OTPRequest
- Fields:
  - `id`
  - `user: FK -> User, null=True`
  - `phone_number: CharField(20)`
  - `request_type: CharField(30)`
  - `purpose_reference: CharField(100, blank=True)`
  - `otp_hash: CharField(255)`
  - `status: CharField(20)`
  - `attempts_count: PositiveSmallIntegerField(default=0)`
  - `max_attempts: PositiveSmallIntegerField(default=5)`
  - `expires_at: DateTimeField()`
  - `verified_at: DateTimeField(null=True)`
  - `sent_via: CharField(20, default='SMS')`
  - `ip_address: GenericIPAddressField(null=True)`
  - `device_id: CharField(128, blank=True)`
  - `created_at`
- Relationships:
  - many-to-one to `User`
- Constraints:
  - store hashed OTP only
  - supports registration before activation
- Indexes:
  - composite `(phone_number, created_at)`
  - composite `(request_type, status)`
  - `expires_at`
  - `purpose_reference`

### LoginLog
- Fields:
  - `id`
  - `user: FK -> User, null=True`
  - `phone_number: CharField(20)`
  - `device: CharField(255, blank=True)`
  - `device_id: CharField(128, blank=True)`
  - `ip_address: GenericIPAddressField(null=True)`
  - `user_agent: TextField(blank=True)`
  - `location_country: CharField(100, blank=True)`
  - `location_city: CharField(100, blank=True)`
  - `status: CharField(20)`
  - `failure_reason: CharField(100, blank=True)`
  - `risk_score: DecimalField(5,2, null=True)`
  - `attempted_at`
- Relationships:
  - many-to-one to `User`
- Constraints:
  - capture both successful and failed login attempts
- Indexes:
  - composite `(phone_number, attempted_at)`
  - composite `(user_id, attempted_at)`
  - composite `(status, attempted_at)`
  - `device_id`

### UserDevice
- Fields:
  - `id`
  - `user: FK -> User`
  - `device_uuid: CharField(128, unique=True)`
  - `device_name: CharField(255, blank=True)`
  - `platform: CharField(30, blank=True)`
  - `os_version: CharField(50, blank=True)`
  - `app_version: CharField(50, blank=True)`
  - `device_hash: CharField(255)`
  - `is_trusted: BooleanField(default=False)`
  - `is_active: BooleanField(default=True)`
  - `first_seen_at`
  - `last_seen_at: DateTimeField(null=True)`
  - `last_login_ip: GenericIPAddressField(null=True)`
- Relationships:
  - many-to-one to `User`
- Constraints:
  - no biometric material stored
- Indexes:
  - unique `device_uuid`
  - composite `(user_id, is_trusted)`
  - `last_seen_at`

### AccountLockEvent
- Fields:
  - `id`
  - `user: FK -> User`
  - `event_type: CharField(20)`
  - `reason: CharField(255)`
  - `trigger_source: CharField(30)`
  - `locked_by: FK -> User, null=True`
  - `unlocked_by: FK -> User, null=True`
  - `occurred_at`
  - `resolved_at: DateTimeField(null=True)`
  - `is_active: BooleanField(default=True)`
  - `metadata_json: JSONField(default=dict, blank=True)`
- Relationships:
  - many-to-one to `User`
- Constraints:
  - used for login-access lock state, separate from account financial restrictions
- Indexes:
  - composite `(user_id, is_active)`
  - composite `(event_type, occurred_at)`

### PasswordResetAudit
- Fields:
  - `id`
  - `user: FK -> User`
  - `reset_type: CharField(20)`
  - `initiated_by: FK -> User, null=True`
  - `otp_request: FK -> OTPRequest, null=True`
  - `reason: CharField(255, blank=True)`
  - `ip_address: GenericIPAddressField(null=True)`
  - `success: BooleanField(default=False)`
  - `created_at`
- Relationships:
  - many-to-one to `User`
  - optional many-to-one to `OTPRequest`
- Constraints:
  - `reset_type` values: `PASSWORD`, `PIN`
- Indexes:
  - composite `(user_id, created_at)`
  - composite `(initiated_by_id, created_at)`
  - composite `(reset_type, success)`

## Support, Notification, and Risk Models

### SupportTicket
- Fields:
  - `id`
  - `ticket_number: CharField(30, unique=True)`
  - `customer: FK -> User`
  - `subject: CharField(255)`
  - `description: TextField()`
  - `category: CharField(50)`
  - `priority: CharField(20)`
  - `status: CharField(20)`
  - `related_transaction: FK -> Transaction, null=True`
  - `related_account: FK -> Account, null=True`
  - `assigned_to: FK -> User, null=True`
  - `resolution_notes: TextField(blank=True)`
  - `opened_at`
  - `resolved_at: DateTimeField(null=True)`
  - `closed_at: DateTimeField(null=True)`
- Relationships:
  - many-to-one to customer `User`
  - optional many-to-one to handling staff `User`
- Constraints:
  - `assigned_to` should be `CUSTOMER_SERVICE` or an approved escalation role
- Indexes:
  - unique `ticket_number`
  - composite `(customer_id, status)`
  - composite `(assigned_to_id, status)`
  - `opened_at`

### Notification
- Fields:
  - `id`
  - `user: FK -> User`
  - `channel: CharField(20)`
  - `notification_type: CharField(50)`
  - `title: CharField(255)`
  - `message: TextField()`
  - `status: CharField(20)`
  - `transaction: FK -> Transaction, null=True`
  - `support_ticket: FK -> SupportTicket, null=True`
  - `sent_at: DateTimeField(null=True)`
  - `read_at: DateTimeField(null=True)`
  - `created_at`
- Relationships:
  - many-to-one to `User`
  - optional many-to-one to `Transaction`
  - optional many-to-one to `SupportTicket`
- Constraints:
  - channel values should come from supported delivery adapters
- Indexes:
  - composite `(user_id, status)`
  - composite `(channel, status)`
  - `created_at`

### FraudAlert
- Fields:
  - `id`
  - `transaction: FK -> Transaction, null=True`
  - `login_log: FK -> LoginLog, null=True`
  - `user: FK -> User, null=True`
  - `alert_type: CharField(50)`
  - `fraud_score: DecimalField(5,2)`
  - `risk_level: CharField(20)`
  - `status: CharField(20)`
  - `triggered_by: CharField(30)`
  - `reason_code: CharField(50)`
  - `summary: TextField()`
  - `metadata_json: JSONField(default=dict, blank=True)`
  - `created_at`
- Relationships:
  - many-to-one to `Transaction`
  - many-to-one to `LoginLog`
  - many-to-one to `User`
  - one `FraudAlert` to many `FraudDecision`
- Constraints:
  - at least one of `transaction` or `login_log` must be present
- Indexes:
  - composite `(status, risk_level)`
  - composite `(transaction_id, created_at)`
  - composite `(user_id, created_at)`
  - `reason_code`

### FraudDecision
- Fields:
  - `id`
  - `fraud_alert: FK -> FraudAlert`
  - `decision_by: FK -> User`
  - `outcome: CharField(30)`
  - `action_taken: CharField(100, blank=True)`
  - `notes: TextField(blank=True)`
  - `account_restriction: FK -> AccountRestriction, null=True`
  - `decided_at`
- Relationships:
  - many-to-one to `FraudAlert`
  - many-to-one to decision-maker `User`
- Constraints:
  - `decision_by` should be `RISK_OFFICER` or `ADMIN`
- Indexes:
  - composite `(fraud_alert_id, decided_at)`
  - composite `(decision_by_id, decided_at)`
  - `outcome`

## Key Relational Rules
- `User` owns one or more `Account` records.
- `MerchantProfile` extends a merchant `User` and points to one settlement `Account`.
- Every monetary event creates one `Transaction` plus multiple `TransactionEntry` rows.
- `TransactionEntry` is the source of truth for account debits and credits.
- `QRPayment` and `BillPayment` are channel-specific extensions of `Transaction`.
- `AccountRestriction` tracks freeze, block, and release history without losing audit state.
- `OTPRequest`, `LoginLog`, `UserDevice`, and `AccountLockEvent` support security analytics and incident review.
- `FraudAlert` stores machine or rules-based signals; `FraudDecision` stores reviewed outcomes for ML labeling.
- `SupportTicket` and `Notification` keep operational support and customer communication traceable.

## Banking-Grade Implementation Notes
- Use MySQL `utf8mb4`, `InnoDB`, and strict SQL mode.
- Use `DecimalField` for all amounts; never use floating point types.
- Wrap transaction posting in database transactions with row-level locking on affected accounts.
- Keep transaction and entry rows immutable after posting; reversals should create new rows.
- Add service-layer checks so users in `PENDING_VERIFICATION` cannot create `Transaction` rows for money movement.
- Audit all staff approvals, resets, restrictions, and fraud decisions.
- Retain OTP, login, device, fraud, and transaction metadata long enough for compliance and model training.
