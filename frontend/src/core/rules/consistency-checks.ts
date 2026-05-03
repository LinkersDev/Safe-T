export const consistencyChecks = {
  kyc: ['payment_routes_require_KYC_APPROVED', 'kyc_status_refresh_updates_rule_state'],
  accounts: ['payment_source_account_must_be_ACTIVE', 'restricted_accounts_disabled_in_forms'],
  ledger: ['uncertain_payment_errors_show_reconciliation_copy', 'completed_transactions_only_for_staff_reversal'],
  staff: ['staff_routes_require_staff_role', 'sensitive_staff_routes_require_permission_hint'],
} as const
