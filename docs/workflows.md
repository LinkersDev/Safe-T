# SafeT Core Workflows

## 1. Registration Flow

### Customer self-registration
1. Customer submits phone number.
2. System normalizes the phone number and checks uniqueness.
3. System creates an `OTPRequest` with `request_type=REGISTRATION`.
4. Customer submits OTP.
5. System verifies the OTP and marks the phone as verified.
6. Customer sets password and PIN.
7. System creates a `User` with:
   - role = `CUSTOMER`
   - `status = PENDING_VERIFICATION`
   - `is_phone_verified = True`
8. Optional KYC files are uploaded to `KycDocument`.
9. A default customer `Account` may be created immediately, but it remains non-operational until approval.

### Pending-access rules
- A `PENDING_VERIFICATION` user can log in.
- A `PENDING_VERIFICATION` user can view onboarding status and upload missing KYC.
- A `PENDING_VERIFICATION` user cannot initiate:
  - transfer
  - withdrawal
  - QR payment
  - bill payment

### Staff activation
1. `Teller` or `Admin` reviews customer details and KYC.
2. Staff approves or rejects the customer.
3. On approval:
   - `User.status = ACTIVE`
   - `approved_by` is set
   - `approved_at` is set
4. On rejection:
   - `User.status = REJECTED`
   - `rejection_reason` is set

## 2. Login Flow
1. User enters phone number.
2. System looks up the user by normalized phone number only.
3. System creates an `OTPRequest` with `request_type=LOGIN`.
4. OTP is delivered via approved channel.
5. User submits OTP.
6. System validates OTP expiry, status, and attempt count.
7. User submits password or PIN based on client policy.
8. System evaluates device context:
   - existing `UserDevice`
   - trusted flag
   - IP address
   - app version
9. System writes a `LoginLog`.
10. If repeated failures or anomaly rules trigger, create `AccountLockEvent` and optionally `FraudAlert`.
11. If successful, issue authenticated session/token.

## 3. Transaction Flow

### Common ledger rules
- Every money movement creates exactly one `Transaction`.
- Every `Transaction` creates balanced `TransactionEntry` rows.
- Posting must happen inside one DB transaction.
- A completed transaction cannot be edited; reversal creates a new transaction.

### Transfer
1. Active customer selects source account and destination beneficiary.
2. System validates:
   - user status is `ACTIVE`
   - account status is `ACTIVE`
   - sufficient available balance
   - destination account validity
3. System creates `OTPRequest` with `request_type=TRANSFER`.
4. After OTP verification, system creates `Transaction` with `transaction_type=TRANSFER`.
5. System posts debit and credit `TransactionEntry` rows.
6. Fee entries are added if `FeeRule` applies.
7. System updates balances and emits `Notification`.

### Deposit
1. `Teller` identifies customer and source of funds.
2. System validates target account state.
3. System creates `Transaction` with `transaction_type=DEPOSIT`.
4. Ledger entries credit the customer account and debit the internal cash/branch account.
5. System updates balances and audit logs.

### Withdrawal
1. `Teller` verifies customer identity.
2. System validates customer status, account status, and balance.
3. System creates `Transaction` with `transaction_type=WITHDRAWAL`.
4. Ledger entries debit the customer account and credit the internal cash/branch account.
5. System updates balances and audit logs.

### QR payment
1. Merchant QR resolves to `MerchantProfile` and settlement `Account`.
2. Customer scans QR and confirms amount.
3. System creates `OTPRequest` with `request_type=QR_PAYMENT`.
4. After OTP verification, system creates:
   - `Transaction(transaction_type=QR_PAYMENT)`
   - `QRPayment`
   - balanced ledger entries
5. Customer and merchant receive `Notification` records.

### Bill payment
1. Customer selects provider and enters service number.
2. System fetches bill data and stores payment context.
3. System creates `OTPRequest` with `request_type=BILL_PAYMENT`.
4. After OTP verification, system creates:
   - `Transaction(transaction_type=BILL_PAYMENT)`
   - `BillPayment`
   - balanced ledger entries
5. System applies fee rules if configured.
6. Customer receives payment confirmation notification.

## 4. Fraud Flow
1. Login or transaction activity produces risk features.
2. Rules engine and/or ML service generates a score.
3. System creates `FraudAlert` when thresholds are crossed.
4. Risk Officer reviews the alert with linked:
   - transaction
   - login history
   - device context
   - recent OTP activity
5. Risk Officer records `FraudDecision`.
6. If required, system creates `AccountRestriction`:
   - freeze
   - block
7. Related account or user access can also be restricted with `AccountLockEvent`.
8. Final reviewed outcomes remain stored for reporting and model training.

## 5. Password and PIN Reset Flow
1. User or staff starts reset request.
2. System creates `OTPRequest` with the relevant reset type.
3. After OTP verification or staff-assisted verification, new password or PIN is set.
4. System writes `PasswordResetAudit`.
5. If the reset is support-assisted, optionally notify the user and flag high-risk sessions.

## 6. Support Flow
1. Customer issue is logged as `SupportTicket`.
2. Ticket may reference a transaction or account.
3. `Customer Service` staff is assigned.
4. Staff updates status until resolution.
5. Resolution notes and close timestamps remain stored for audit.
