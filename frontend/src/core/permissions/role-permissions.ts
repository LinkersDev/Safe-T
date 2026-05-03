import type { RoleCode } from '../state/auth-state'

const ROLE_PERMISSIONS: Record<RoleCode, string[]> = {
  CUSTOMER: [],
  MERCHANT_CUSTOMER: [],
  ADMIN: [
    'approve_user',
    'reject_user',
    'block_user',
    'view_all_users',
    'freeze_account',
    'block_account',
    'unfreeze_account',
    'view_all_accounts',
    'view_all_transactions',
    'reverse_transaction',
    'manage_system',
    'review_kyc',
    'review_fraud_alert',
    'manage_support_tickets',
    'unlock_user',
    'reset_user_credentials',
    'staff_deposit',
    'staff_withdraw',
  ],
  TELLER: [
    'approve_user',
    'reject_user',
    'view_all_accounts',
    'staff_register_customer',
    'staff_deposit',
    'staff_withdraw',
    'staff_view_account_transactions',
  ],
  TELLER_ADMIN: [
    'approve_user',
    'reject_user',
    'view_all_users',
    'freeze_account',
    'unfreeze_account',
    'view_all_accounts',
    'view_all_transactions',
  ],
  CUSTOMER_SERVICE: ['manage_support_tickets', 'unlock_user', 'reset_user_credentials'],
  RISK_OFFICER: ['review_fraud_alert'],
}

export function getRolePermissions(role: RoleCode | null) {
  return role ? ROLE_PERMISSIONS[role] : []
}
