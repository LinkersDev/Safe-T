import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { StatCard } from '../../../shared/components/ui/StatCard'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useAuthSession } from '../../security/hooks/useAuthSession'
import { getAdminSummary, getOperationsSummary } from '../services/staff-service'
import type { RoleCode } from '../../../core/state/auth-state'

/* ── role-specific display config ─────────────────────────────────────── */

type AccentColor = 'violet' | 'amber' | 'rose' | 'emerald' | 'blue' | 'indigo' | 'slate'

type RoleConfig = {
  accent: AccentColor
  headline: string
  subtitle: string
  moduleLinks: { label: string; path: string; icon: string; desc: string }[]
  statSelector: (a: Record<string, unknown>, o: Record<string, unknown>) => Array<{
    label: string; value: unknown; icon: string; accent: AccentColor
  }>
}

const ALL_MODULES: { label: string; path: string; icon: string; desc: string }[] = [
  { label: 'User Management',  path: ROUTE_PATHS.staffUsers,    icon: '👤', desc: 'Approve, reject, or block users' },
  { label: 'KYC Review',       path: ROUTE_PATHS.staffKyc,      icon: '✓',  desc: 'Verify identity documents' },
  { label: 'Accounts',         path: ROUTE_PATHS.staffAccounts, icon: '🏦', desc: 'Lookup accounts and customer KYC' },
  { label: 'Register Customer', path: ROUTE_PATHS.staffTellerRegisterCustomer, icon: '＋', desc: 'Open a new customer account' },
  { label: 'Deposit',           path: ROUTE_PATHS.staffTellerDeposit, icon: '⬇', desc: 'Deposit money into an account' },
  { label: 'Withdraw',          path: ROUTE_PATHS.staffTellerWithdraw, icon: '⬆', desc: 'Withdraw money from an account' },
  { label: 'Account Transactions', path: ROUTE_PATHS.staffTellerAccountTransactions, icon: '↕', desc: 'View transactions for an account' },
  { label: 'Ledger',           path: ROUTE_PATHS.staffLedger,   icon: '📒', desc: 'View and reverse transactions' },
  { label: 'Support',          path: ROUTE_PATHS.staffSupport,  icon: '✉',  desc: 'Assign and resolve tickets' },
  { label: 'Risk Alerts',      path: ROUTE_PATHS.staffRisk,     icon: '⚠',  desc: 'Review fraud alerts' },
  { label: 'Reports',          path: ROUTE_PATHS.staffReports,  icon: '📊', desc: 'Platform summaries' },
]

const ROLE_CONFIGS: Partial<Record<RoleCode, RoleConfig>> = {
  ADMIN: {
    accent: 'violet',
    headline: 'Platform Control Center',
    subtitle: 'Full administrative access',
    moduleLinks: ALL_MODULES,
    statSelector: (a, o) => [
      { label: 'Total Users',        value: a.total_users,            icon: '👤', accent: 'violet' },
      { label: 'Pending KYC',        value: o.pending_kyc_users,      icon: '✓',  accent: 'amber'  },
      { label: 'Open Tickets',       value: o.open_support_tickets,   icon: '✉',  accent: 'blue'   },
      { label: 'Total Transactions', value: a.total_transaction_count, icon: '↕', accent: 'violet' },
      { label: 'Active Users',       value: a.active_users,           icon: '🏦', accent: 'slate'  },
      { label: 'Blocked Users',      value: a.blocked_users,          icon: '⚠',  accent: 'rose'   },
    ],
  },
  TELLER_ADMIN: {
    accent: 'amber',
    headline: 'Teller Operations',
    subtitle: 'User approvals and account management',
    moduleLinks: ALL_MODULES.filter(m =>
      ([ROUTE_PATHS.staffUsers, ROUTE_PATHS.staffAccounts, ROUTE_PATHS.staffKyc, ROUTE_PATHS.staffLedger, ROUTE_PATHS.staffReports] as string[]).includes(m.path)
    ),
    statSelector: (a, o) => [
      { label: 'Pending Users',   value: o.pending_users,            icon: '👤', accent: 'amber' as AccentColor },
      { label: 'Pending KYC',     value: o.pending_kyc_users,        icon: '✓',  accent: 'amber' as AccentColor },
      { label: 'Transactions',    value: a.total_transaction_count,  icon: '↕',  accent: 'amber' as AccentColor },
    ],
  },
  TELLER: {
    accent: 'amber',
    headline: 'Teller Operations',
    subtitle: 'User approvals and account management',
    moduleLinks: ALL_MODULES.filter(m =>
      ([ROUTE_PATHS.staffAccounts, ROUTE_PATHS.staffTellerRegisterCustomer, ROUTE_PATHS.staffTellerDeposit, ROUTE_PATHS.staffTellerWithdraw, ROUTE_PATHS.staffTellerAccountTransactions] as string[]).includes(m.path)
    ),
    statSelector: (_a, _o) => [],
  },
  RISK_OFFICER: {
    accent: 'rose',
    headline: 'Risk & Fraud Center',
    subtitle: 'Monitor and act on fraud alerts',
    moduleLinks: ALL_MODULES.filter(m =>
      ([ROUTE_PATHS.staffRisk] as string[]).includes(m.path)
    ),
    statSelector: (_a, o) => [
      { label: 'Open Tickets',    value: o.open_support_tickets,     icon: '⚠',  accent: 'rose'  as AccentColor },
      { label: 'Pending KYC',     value: o.pending_kyc_users,        icon: '✓',  accent: 'amber' as AccentColor },
    ],
  },
  CUSTOMER_SERVICE: {
    accent: 'emerald',
    headline: 'Support Operations',
    subtitle: 'Manage customer tickets and requests',
    moduleLinks: ALL_MODULES.filter(m =>
      ([ROUTE_PATHS.staffSupport] as string[]).includes(m.path)
    ),
    statSelector: (_a, o) => [
      { label: 'Open Tickets',    value: o.open_support_tickets,     icon: '✉',  accent: 'emerald' as AccentColor },
      { label: 'Unassigned',      value: o.unassigned_tickets,       icon: '⏱',  accent: 'blue'    as AccentColor },
    ],
  },
}

export function StaffDashboardPage() {
  const { user, permissions } = useAuthSession()

  const canLoadAdminSummary = permissions.includes('view_all_transactions')
  const canLoadOpsSummary = permissions.includes('review_kyc') || permissions.includes('manage_support_tickets')

  const adminSummary = useQuery({
    queryKey: ['staff-admin-summary'],
    queryFn: getAdminSummary,
    enabled: canLoadAdminSummary,
  })
  const opsSummary = useQuery({
    queryKey: ['staff-ops-summary'],
    queryFn: getOperationsSummary,
    enabled: canLoadOpsSummary,
  })

  const role = (user?.role ?? 'ADMIN') as RoleCode
  const config = ROLE_CONFIGS[role] ?? ROLE_CONFIGS.ADMIN!

  const loading =
    (canLoadAdminSummary && adminSummary.isLoading) ||
    (canLoadOpsSummary && opsSummary.isLoading)

  const degraded =
    (canLoadAdminSummary && adminSummary.failureCount >= 2) ||
    (canLoadOpsSummary && opsSummary.failureCount >= 2)

  const a = (adminSummary.data ?? {}) as Record<string, unknown>
  const o = (opsSummary.data ?? {}) as Record<string, unknown>
  const stats = config.statSelector(a, o)

  return (
    <div className="space-y-6">
      {degraded && (
        <StatusNoticeCard
          title="Degraded mode"
          message="Some dashboard data is unstable due to repeated API failures."
          variant="warning"
        />
      )}
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-text-primary">
          {config.headline}
        </h2>
        <p className="mt-0.5 text-sm text-text-tertiary">
          {user?.fullName} · {config.subtitle}
        </p>
      </div>

      {/* Stat cards */}
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {stats.map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {stats.map(({ label, value, icon, accent }) => (
            <StatCard
              key={label}
              label={label}
              value={String(value ?? '—')}
              icon={icon}
              accent={accent}
            />
          ))}
        </div>
      )}

      {/* Module links */}
      {config.moduleLinks.length > 0 && (
        <div>
          <p className="mb-3 text-sm font-semibold text-text-secondary">Modules</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {config.moduleLinks.map(({ label, path, icon, desc }) => (
              <Link
                key={path}
                to={path}
                className="flex items-start gap-3 rounded-xl border border-border bg-surface-primary p-4 shadow-sm hover:shadow-md transition-all"
              >
                <span className="text-2xl">{icon}</span>
                <div>
                  <p className="font-semibold text-text-primary">{label}</p>
                  <p className="text-xs text-text-tertiary mt-0.5">{desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
