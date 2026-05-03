import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { StatCard } from '../../../shared/components/ui/StatCard'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { DataTable, type Column } from '../../../shared/components/ui/DataTable'
import { Badge } from '../../../shared/components/ui/Badge'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import {
  getAdminSummary,
  getOperationsSummary,
  getUserGrowth,
  getTransactionVolume,
  getTransactionsByType,
  getRiskSummary,
  getRecentTransactions,
} from '../../staff/services/staff-service'
import type { StaffTransaction } from '../../staff/types'
import { cn } from '../../../core/utils/cn'

type TabId = 'platform' | 'operations' | 'risk' | 'transactions'

const TABS: { id: TabId; label: string }[] = [
  { id: 'platform',     label: 'Platform' },
  { id: 'operations',   label: 'Operations' },
  { id: 'risk',         label: 'Risk' },
  { id: 'transactions', label: 'Transactions' },
]

export function StaffReportsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('platform')

  const adminSummary = useQuery({ queryKey: ['staff-admin-summary'],  queryFn: getAdminSummary,          enabled: activeTab === 'platform' })
  const opsSummary   = useQuery({ queryKey: ['staff-ops-summary'],    queryFn: getOperationsSummary,     enabled: activeTab === 'operations' })
  const userGrowth   = useQuery({ queryKey: ['staff-user-growth'],    queryFn: getUserGrowth,            enabled: activeTab === 'platform' })
  const txVolume     = useQuery({ queryKey: ['staff-tx-volume'],      queryFn: getTransactionVolume,     enabled: activeTab === 'platform' })
  const txByType     = useQuery({ queryKey: ['staff-tx-by-type'],     queryFn: getTransactionsByType,    enabled: activeTab === 'platform' })
  const riskSummary  = useQuery({ queryKey: ['staff-risk-summary'],   queryFn: getRiskSummary,           enabled: activeTab === 'risk' })
  const recentTx     = useQuery({ queryKey: ['staff-recent-tx'],      queryFn: getRecentTransactions,    enabled: activeTab === 'transactions' })
  const degraded = [adminSummary, opsSummary, userGrowth, txVolume, txByType, riskSummary, recentTx].some((q) => q.failureCount >= 2)

  const txColumns: Column<StaffTransaction>[] = [
    {
      key: 'ref',
      header: 'Reference',
      render: (tx) => <span className="font-mono text-xs text-text-secondary">{tx.reference}</span>,
    },
    {
      key: 'type',
      header: 'Type',
      render: (tx) => (
        <span className="rounded bg-surface-secondary px-2 py-0.5 text-xs font-medium text-text-secondary">
          {tx.type.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      render: (tx) => (
        <span className="font-bold text-sm text-text-primary">
          {tx.currency} {Number(tx.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (tx) => (
        <Badge
          variant={
            tx.status === 'COMPLETED' ? 'success' :
            tx.status === 'FAILED' ? 'danger' :
            tx.status === 'REVERSED' ? 'info' : 'warning'
          }
        >
          {tx.status}
        </Badge>
      ),
    },
    {
      key: 'date',
      header: 'Date',
      render: (tx) => (
        <span className="text-xs text-text-tertiary">{new Date(tx.createdAt).toLocaleString()}</span>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      {degraded && (
        <StatusNoticeCard
          title="Reporting degraded"
          message="One or more reporting endpoints are unstable. Values may be partial."
          variant="warning"
        />
      )}
      {/* Tab bar */}
      <div className="flex gap-1 rounded-xl border border-border bg-surface-secondary p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'bg-surface-primary text-text-primary shadow-sm'
                : 'text-text-secondary hover:text-text-primary',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Platform tab */}
      {activeTab === 'platform' && (
        <div className="space-y-6">
          {adminSummary.isError && (
            <StatusNoticeCard
              title="Platform metrics unavailable"
              message="Unable to load admin summary."
              variant="error"
            />
          )}
          {adminSummary.isLoading ? (
            <div className="grid gap-4 sm:grid-cols-3">
              {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
            </div>
          ) : (
            <>
              <section>
                <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  User Metrics
                </h3>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <StatCard label="Total Users"    value={String(adminSummary.data?.total_users ?? '—')}        icon="👤" accent="violet" />
                  <StatCard label="Active Users"   value={String(adminSummary.data?.active_users ?? '—')}       icon="✓"  accent="violet" />
                  <StatCard label="Pending Users"  value={String(adminSummary.data?.pending_users ?? '—')}      icon="⏳" accent="amber" />
                  <StatCard label="Blocked Users"  value={String(adminSummary.data?.blocked_users ?? '—')}      icon="🚫" accent="rose" />
                </div>
              </section>
              <section>
                <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  Transaction Metrics
                </h3>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <StatCard label="Total Tx Count"   value={String(adminSummary.data?.total_transaction_count ?? '—')}   icon="↕" accent="indigo" />
                  <StatCard label="Total Volume USD"  value={String(adminSummary.data?.total_transaction_volume ?? '—')} icon="💵" accent="indigo" />
                </div>
              </section>
            </>
          )}

          {/* User growth table */}
          {!userGrowth.isLoading && (userGrowth.data?.length ?? 0) > 0 && (
            <section>
              <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                User Growth (daily)
              </h3>
              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full text-sm">
                  <thead className="border-b border-border bg-surface-secondary">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-text-tertiary">Date</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-text-tertiary">New Users</th>
                    </tr>
                  </thead>
                  <tbody>
                    {userGrowth.data?.map((row) => (
                      <tr key={row.date} className="border-b border-border last:border-0">
                        <td className="px-4 py-2 text-text-primary">{row.date}</td>
                        <td className="px-4 py-2 font-semibold text-indigo-600">{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Tx by type table */}
          {!txByType.isLoading && (txByType.data?.length ?? 0) > 0 && (
            <section>
              <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                Transactions by Type
              </h3>
              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full text-sm">
                  <thead className="border-b border-border bg-surface-secondary">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-text-tertiary">Type</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-text-tertiary">Count</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-text-tertiary">Total (USD)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {txByType.data?.map((row) => (
                      <tr key={row.type} className="border-b border-border last:border-0">
                        <td className="px-4 py-2 font-medium text-text-primary">{row.type.replace(/_/g, ' ')}</td>
                        <td className="px-4 py-2 text-text-secondary">{row.count}</td>
                        <td className="px-4 py-2 font-semibold text-emerald-600">
                          {Number(row.total).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}

      {/* Operations tab */}
      {activeTab === 'operations' && (
        <div className="space-y-6">
          {opsSummary.isError && (
            <StatusNoticeCard
              title="Operations metrics unavailable"
              message="Unable to load operations summary."
              variant="error"
            />
          )}
          {opsSummary.isLoading ? (
            <div className="grid gap-4 sm:grid-cols-3">
              {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <StatCard label="Pending KYC Users" value={String(opsSummary.data?.pending_kyc_users ?? '—')}      icon="📋" accent="amber" />
              <StatCard label="Pending KYC Docs"  value={String(opsSummary.data?.pending_kyc_docs ?? '—')}       icon="📄" accent="amber" />
              <StatCard label="Open Tickets"      value={String(opsSummary.data?.open_support_tickets ?? '—')}   icon="✉"  accent="slate" />
              <StatCard label="Unassigned Tickets" value={String(opsSummary.data?.unassigned_tickets ?? '—')}    icon="📌" accent="slate" />
              <StatCard label="Txns Last Hour"    value={String(opsSummary.data?.transactions_last_hour ?? '—')} icon="⏱"  accent="emerald" />
            </div>
          )}
        </div>
      )}

      {/* Risk tab */}
      {activeTab === 'risk' && (
        <div className="space-y-6">
          {riskSummary.isError && (
            <StatusNoticeCard
              title="Risk metrics unavailable"
              message="Unable to load risk summary."
              variant="error"
            />
          )}
          {riskSummary.isLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Total Alerts"      value={String(riskSummary.data?.total_alerts ?? '—')}    icon="⚠"  accent="rose" />
              <StatCard label="Open Alerts"       value={String(riskSummary.data?.open_alerts ?? '—')}     icon="🔓" accent="rose" />
              <StatCard label="Critical Alerts"   value={String(riskSummary.data?.critical_alerts ?? '—')} icon="🔴" accent="rose" />
              <StatCard label="Dismissed Today"   value={String(riskSummary.data?.dismissed_today ?? '—')} icon="✓"  accent="slate" />
            </div>
          )}
        </div>
      )}

      {/* Transactions tab */}
      {activeTab === 'transactions' && (
        <div className="space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
            Recent Transactions
          </h3>
          {recentTx.isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-14 w-full rounded-xl" />)}
            </div>
          ) : recentTx.isError ? (
            <StatusNoticeCard
              title="Recent transactions unavailable"
              message="Unable to load transactions feed."
              variant="error"
            />
          ) : (
            <DataTable
              columns={txColumns}
              rows={recentTx.data ?? []}
              keyExtractor={(tx) => tx.id}
              emptyMessage="No recent transactions."
            />
          )}
        </div>
      )}
    </div>
  )
}
