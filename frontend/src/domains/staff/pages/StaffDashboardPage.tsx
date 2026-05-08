import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import type { LucideIcon } from 'lucide-react'
import {
  Users,
  ShieldCheck,
  Landmark,
  ArrowDownToLine,
  ArrowUpFromLine,
  BookOpen,
  MessageSquare,
  AlertTriangle,
  BarChart3,
  UserPlus,
  ArrowLeftRight,
} from 'lucide-react'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { StatCard } from '../../../shared/components/ui/StatCard'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useAuthSession } from '../../security/hooks/useAuthSession'
import { getAdminSummary, getOperationsSummary } from '../services/staff-service'
import type { RoleCode } from '../../../core/state/auth-state'

/* ── role-specific display config ─────────────────────────────────────── */

type AccentColor = 'blue' | 'green' | 'amber' | 'rose' | 'slate'

type ModuleLink = { label: string; path: string; icon: LucideIcon; desc: string; accent: AccentColor }

type RoleConfig = {
  headline: string
  subtitle: string
  moduleLinks: ModuleLink[]
  statSelector: (a: Record<string, unknown>, o: Record<string, unknown>) => Array<{
    label: string; value: unknown; icon: LucideIcon; accent: AccentColor
  }>
}

const ALL_MODULES: ModuleLink[] = [
  { label: 'User Management',  path: ROUTE_PATHS.staffUsers,    icon: Users, desc: 'Approve, reject, or block users', accent: 'blue' },
  { label: 'KYC Review',       path: ROUTE_PATHS.staffKyc,      icon: ShieldCheck,  desc: 'Verify identity documents', accent: 'amber' },
  { label: 'Accounts',         path: ROUTE_PATHS.staffAccounts, icon: Landmark, desc: 'Lookup accounts and customer KYC', accent: 'blue' },
  { label: 'Register Customer', path: ROUTE_PATHS.staffTellerRegisterCustomer, icon: UserPlus, desc: 'Open a new customer account', accent: 'green' },
  { label: 'Deposit',           path: ROUTE_PATHS.staffTellerDeposit, icon: ArrowDownToLine, desc: 'Deposit money into an account', accent: 'green' },
  { label: 'Withdraw',          path: ROUTE_PATHS.staffTellerWithdraw, icon: ArrowUpFromLine, desc: 'Withdraw money from an account', accent: 'amber' },
  { label: 'Account Transactions', path: ROUTE_PATHS.staffTellerAccountTransactions, icon: ArrowLeftRight, desc: 'View transactions for an account', accent: 'blue' },
  { label: 'Ledger',           path: ROUTE_PATHS.staffLedger,   icon: BookOpen, desc: 'View and reverse transactions', accent: 'blue' },
  { label: 'Support',          path: ROUTE_PATHS.staffSupport,  icon: MessageSquare,  desc: 'Assign and resolve tickets', accent: 'green' },
  { label: 'Risk Alerts',      path: ROUTE_PATHS.staffRisk,     icon: AlertTriangle,  desc: 'Review fraud alerts', accent: 'rose' },
  { label: 'Reports',          path: ROUTE_PATHS.staffReports,  icon: BarChart3, desc: 'Platform summaries', accent: 'blue' },
]

const ROLE_CONFIGS: Partial<Record<RoleCode, RoleConfig>> = {
  ADMIN: {
    headline: 'Platform Control Center',
    subtitle: 'Full administrative access',
    moduleLinks: ALL_MODULES,
    statSelector: (a, o) => [
      { label: 'Total Users',        value: a.total_users,            icon: Users, accent: 'blue' },
      { label: 'Pending KYC',        value: o.pending_kyc_users,      icon: ShieldCheck, accent: 'amber' },
      { label: 'Open Tickets',       value: o.open_support_tickets,   icon: MessageSquare, accent: 'blue' },
      { label: 'Total Transactions', value: a.total_transaction_count, icon: ArrowLeftRight, accent: 'blue' },
      { label: 'Active Users',       value: a.active_users,           icon: Landmark, accent: 'slate' },
      { label: 'Blocked Users',      value: a.blocked_users,          icon: AlertTriangle, accent: 'rose' },
    ],
  },
  TELLER_ADMIN: {
    headline: 'Teller Operations',
    subtitle: 'User approvals and account management',
    moduleLinks: ALL_MODULES.filter(m =>
      ([ROUTE_PATHS.staffUsers, ROUTE_PATHS.staffAccounts, ROUTE_PATHS.staffKyc, ROUTE_PATHS.staffLedger, ROUTE_PATHS.staffReports] as string[]).includes(m.path)
    ),
    statSelector: (a, o) => [
      { label: 'Pending Users',   value: o.pending_users,            icon: Users, accent: 'amber' },
      { label: 'Pending KYC',     value: o.pending_kyc_users,        icon: ShieldCheck, accent: 'amber' },
      { label: 'Transactions',    value: a.total_transaction_count,  icon: ArrowLeftRight, accent: 'amber' },
    ],
  },
  TELLER: {
    headline: 'Teller Operations',
    subtitle: 'User approvals and account management',
    moduleLinks: ALL_MODULES.filter(m =>
      ([ROUTE_PATHS.staffAccounts, ROUTE_PATHS.staffTellerRegisterCustomer, ROUTE_PATHS.staffTellerDeposit, ROUTE_PATHS.staffTellerWithdraw, ROUTE_PATHS.staffTellerAccountTransactions] as string[]).includes(m.path)
    ),
    statSelector: (_a, _o) => [],
  },
  RISK_OFFICER: {
    headline: 'Risk & Fraud Center',
    subtitle: 'Monitor and act on fraud alerts',
    moduleLinks: ALL_MODULES.filter(m =>
      ([ROUTE_PATHS.staffRisk] as string[]).includes(m.path)
    ),
    statSelector: (_a, o) => [
      { label: 'Open Tickets',    value: o.open_support_tickets,     icon: AlertTriangle, accent: 'rose' },
      { label: 'Pending KYC',     value: o.pending_kyc_users,        icon: ShieldCheck, accent: 'amber' },
    ],
  },
  CUSTOMER_SERVICE: {
    headline: 'Support Operations',
    subtitle: 'Manage customer tickets and requests',
    moduleLinks: ALL_MODULES.filter(m =>
      ([ROUTE_PATHS.staffSupport] as string[]).includes(m.path)
    ),
    statSelector: (_a, o) => [
      { label: 'Open Tickets',    value: o.open_support_tickets,     icon: MessageSquare, accent: 'green' },
      { label: 'Unassigned',      value: o.unassigned_tickets,       icon: AlertTriangle, accent: 'blue' },
    ],
  },
}

export function StaffDashboardPage() {
  const { user, permissions } = useAuthSession()

  // Show loading if auth session not ready
  if (!user) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="animate-pulse text-slate-500">Loading...</div>
      </div>
    )
  }

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

  const role = user.role as RoleCode
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
    <div className="space-y-8">
      {degraded && (
        <StatusNoticeCard
          title="Degraded mode"
          message="Some dashboard data is unstable due to repeated API failures."
          variant="warning"
        />
      )}
      {/* Header */}
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-slate-900">
          {config.headline}
        </h2>
        <p className="text-sm text-slate-500 leading-relaxed">
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
          {stats.map(({ label, value, icon: Icon, accent }) => (
            <StatCard
              key={label}
              label={label}
              value={String(value ?? '—')}
              icon={Icon}
              accent={accent}
            />
          ))}
        </div>
      )}

      {/* Module links */}
      {config.moduleLinks.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm font-semibold text-slate-900">Modules</p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {config.moduleLinks.map(({ label, path, icon: Icon, desc, accent }) => {
              const accentClasses = {
                blue: 'border-l-blue-500',
                green: 'border-l-emerald-500',
                amber: 'border-l-amber-500',
                rose: 'border-l-rose-500',
                slate: 'border-l-slate-400',
              }
              const iconColors = {
                blue: 'text-blue-600 bg-blue-50',
                green: 'text-emerald-600 bg-emerald-50',
                amber: 'text-amber-600 bg-amber-50',
                rose: 'text-rose-600 bg-rose-50',
                slate: 'text-slate-600 bg-slate-50',
              }
              return (
                <Link
                  key={path}
                  to={path}
                  className={`
                    card-hover flex items-start gap-3 rounded-xl border border-[#E2E8F0] bg-white p-4 relative overflow-hidden
                    ${accentClasses[accent]}
                  `}
                  style={{ 
                    boxShadow: '0 4px 20px rgba(10, 37, 64, 0.08)',
                    borderLeftWidth: '3px',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${iconColors[accent]}`}>
                    <Icon size={20} strokeWidth={2} />
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">{label}</p>
                    <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{desc}</p>
                  </div>
                </Link>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
