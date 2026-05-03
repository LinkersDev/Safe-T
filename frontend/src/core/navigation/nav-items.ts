import type { RoleCode } from '../state/auth-state'
import { ROUTE_PATHS } from '../../app/routing/paths'

export type NavItem = {
  label: string
  path: string
  icon: string
  permission?: string
  group?: 'main' | 'support'
  capability?: keyof typeof BACKEND_CAPABILITIES
}

const BACKEND_CAPABILITIES = {
  staffUsers: true,
  staffKyc: true,
  staffAccounts: true,
  staffLedger: true,
  staffSupport: true,
  staffRisk: true,
  staffReports: true,
} as const

const CUSTOMER_NAV: NavItem[] = [
  { label: 'Dashboard',      path: ROUTE_PATHS.dashboard,    icon: '⊞', group: 'main' },
  { label: 'Transactions',   path: ROUTE_PATHS.ledger,        icon: '↕', group: 'main' },
  { label: 'Transfer',       path: ROUTE_PATHS.transfer,      icon: '→', group: 'main' },
  { label: 'QR Pay',         path: ROUTE_PATHS.qrPayment,     icon: '▣', group: 'main' },
  { label: 'Bill Payment',   path: ROUTE_PATHS.billPayment,   icon: '⚡', group: 'main' },
  { label: 'My Tickets',     path: ROUTE_PATHS.tickets,       icon: '✉', group: 'support' },
  { label: 'Notifications',  path: ROUTE_PATHS.notifications, icon: '🔔', group: 'support' },
  { label: 'My Profile',     path: ROUTE_PATHS.profile,       icon: '⚙', group: 'support' },
]

const ADMIN_NAV: NavItem[] = [
  { label: 'Overview',      path: ROUTE_PATHS.staff,          icon: '⊞' },
  { label: 'Users',         path: ROUTE_PATHS.staffUsers,     icon: '👤', permission: 'view_all_users', capability: 'staffUsers' },
  { label: 'KYC Review',    path: ROUTE_PATHS.staffKyc,       icon: '✓',  permission: 'review_kyc', capability: 'staffKyc' },
  { label: 'Accounts',      path: ROUTE_PATHS.staffAccounts,  icon: '🏦', permission: 'view_all_accounts', capability: 'staffAccounts' },
  { label: 'Deposit',       path: ROUTE_PATHS.staffTellerDeposit, icon: '⬇', permission: 'staff_deposit' },
  { label: 'Withdraw',      path: ROUTE_PATHS.staffTellerWithdraw, icon: '⬆', permission: 'staff_withdraw' },
  { label: 'Ledger',        path: ROUTE_PATHS.staffLedger,    icon: '📒', permission: 'view_all_transactions', capability: 'staffLedger' },
  { label: 'Support',       path: ROUTE_PATHS.staffSupport,   icon: '✉',  permission: 'manage_support_tickets', capability: 'staffSupport' },
  { label: 'Risk Alerts',   path: ROUTE_PATHS.staffRisk,      icon: '⚠',  permission: 'review_fraud_alert', capability: 'staffRisk' },
  { label: 'Reports',       path: ROUTE_PATHS.staffReports,   icon: '📊', permission: 'view_all_transactions', capability: 'staffReports' },
]

const TELLER_NAV: NavItem[] = [
  { label: 'Overview',   path: ROUTE_PATHS.staff,         icon: '⊞' },
  { label: 'Accounts',   path: ROUTE_PATHS.staffAccounts, icon: '🏦', permission: 'view_all_accounts' },
  { label: 'Register',   path: ROUTE_PATHS.staffTellerRegisterCustomer, icon: '＋', permission: 'staff_register_customer' },
  { label: 'Deposit',    path: ROUTE_PATHS.staffTellerDeposit, icon: '⬇', permission: 'staff_deposit' },
  { label: 'Withdraw',   path: ROUTE_PATHS.staffTellerWithdraw, icon: '⬆', permission: 'staff_withdraw' },
  { label: 'Transactions', path: ROUTE_PATHS.staffTellerAccountTransactions, icon: '↕', permission: 'staff_view_account_transactions' },
]

const RISK_NAV: NavItem[] = [
  { label: 'Overview',    path: ROUTE_PATHS.staff,    icon: '⊞' },
  { label: 'Risk Alerts', path: ROUTE_PATHS.staffRisk, icon: '⚠', permission: 'review_fraud_alert' },
]

const CS_NAV: NavItem[] = [
  { label: 'Overview',  path: ROUTE_PATHS.staff,        icon: '⊞' },
  { label: 'Support',   path: ROUTE_PATHS.staffSupport,  icon: '✉', permission: 'manage_support_tickets' },
]

export const NAV_ITEMS: Partial<Record<RoleCode, NavItem[]>> = {
  CUSTOMER: CUSTOMER_NAV,
  ADMIN: ADMIN_NAV,
  TELLER: TELLER_NAV,
  TELLER_ADMIN: ADMIN_NAV,
  RISK_OFFICER: RISK_NAV,
  CUSTOMER_SERVICE: CS_NAV,
}

export function getNavItems(role: RoleCode | null, permissions: string[]): NavItem[] {
  if (!role) return []
  const items = NAV_ITEMS[role] ?? []
  const filtered = items.filter((item) => {
    const permissionAllowed = !item.permission || permissions.includes(item.permission)
    const capabilityAllowed = !item.capability || BACKEND_CAPABILITIES[item.capability]
    return permissionAllowed && capabilityAllowed
  })

  // Safety dedupe by route path to prevent accidental merged duplicates.
  const seen = new Set<string>()
  return filtered.filter((item) => {
    if (seen.has(item.path)) return false
    seen.add(item.path)
    return true
  })
}
