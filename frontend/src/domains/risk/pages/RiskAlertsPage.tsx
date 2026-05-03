import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge } from '../../../shared/components/ui/Badge'
import { DataTable, type Column } from '../../../shared/components/ui/DataTable'
import { StatCard } from '../../../shared/components/ui/StatCard'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { ConfirmationModal } from '../../../shared/components/ui/ConfirmationModal'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import { getRiskAlerts, reviewRiskAlert, type RiskAlertAction } from '../../staff/services/staff-service'
import type { FraudAlert as RiskAlert } from '../../staff/types'

type ActionConfig = {
  action: RiskAlertAction
  label: string
  description: string
  confirmLabel: string
  variant: 'danger' | 'warning'
}

const ACTIONS: ActionConfig[] = [
  {
    action: 'DISMISS',
    label: 'Dismiss',
    description: 'Mark this alert as reviewed and dismissed.',
    confirmLabel: 'Dismiss',
    variant: 'warning',
  },
  {
    action: 'WARN',
    label: 'Warn User',
    description: 'Send a warning to the user associated with this alert.',
    confirmLabel: 'Send Warning',
    variant: 'warning',
  },
  {
    action: 'FREEZE_ACCOUNT',
    label: 'Freeze Account',
    description: 'Temporarily freeze the associated account. The user will not be able to transact.',
    confirmLabel: 'Freeze',
    variant: 'danger',
  },
  {
    action: 'BLOCK_ACCOUNT',
    label: 'Block Account',
    description: 'Permanently block the associated account.',
    confirmLabel: 'Block',
    variant: 'danger',
  },
  {
    action: 'ESCALATE',
    label: 'Escalate',
    description: 'Escalate this alert to senior staff for review.',
    confirmLabel: 'Escalate',
    variant: 'warning',
  },
]

export function RiskAlertsPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [pendingAction, setPendingAction] = useState<{
    alert: RiskAlert
    config: ActionConfig
  } | null>(null)

  const alertsQuery = useQuery({ queryKey: ['risk-alerts'], queryFn: getRiskAlerts })

  const reviewMutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: RiskAlertAction }) =>
      reviewRiskAlert(id, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk-alerts'] })
      setPendingAction(null)
      toast.success('Alert updated successfully.')
    },
    onError: () => {
      toast.error('Failed to update alert. Please try again.')
      setPendingAction(null)
    },
  })

  const alerts = alertsQuery.data ?? []
  const openAlerts    = alerts.filter((a) => a.status === 'OPEN').length
  const criticalCount = alerts.filter((a) => a.severity === 'CRITICAL').length
  const highCount     = alerts.filter((a) => a.severity === 'HIGH').length

  const columns: Column<RiskAlert>[] = [
    {
      key: 'type',
      header: 'Alert Type',
      render: (a) => (
        <div>
          <p className="font-semibold text-text-primary">{a.alertType.replace(/_/g, ' ')}</p>
          <p className="text-xs text-text-tertiary">{a.userName ?? a.accountNumber ?? '—'}</p>
        </div>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (a) => (
        <Badge
          variant={
            a.severity === 'CRITICAL' ? 'danger' :
            a.severity === 'HIGH'     ? 'danger' :
            a.severity === 'MEDIUM'   ? 'warning' : 'info'
          }
        >
          {a.severity}
        </Badge>
      ),
    },
    {
      key: 'score',
      header: 'Score',
      render: (a) => (
        <span className="font-mono text-sm font-bold text-text-primary">{a.riskScore ?? '—'}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (a) => (
        <Badge variant={a.status === 'OPEN' ? 'warning' : a.status === 'DISMISSED' ? 'info' : 'success'}>
          {a.status}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (a) => {
        if (a.status !== 'OPEN') {
          return <span className="text-xs text-text-tertiary">No action</span>
        }
        return (
          <div className="flex flex-wrap gap-1.5">
            {ACTIONS.map((cfg) => (
              <button
                key={cfg.action}
                onClick={(e) => {
                  e.stopPropagation()
                  setPendingAction({ alert: a, config: cfg })
                }}
                className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
                  cfg.variant === 'danger'
                    ? 'border border-rose-200 text-rose-600 hover:bg-rose-50'
                    : 'border border-amber-200 text-amber-600 hover:bg-amber-50'
                }`}
              >
                {cfg.label}
              </button>
            ))}
          </div>
        )
      },
    },
  ]

  if (alertsQuery.isLoading) {
    return <Skeleton className="h-64 w-full rounded-xl" />
  }

  if (alertsQuery.isError) {
    return (
      <StatusNoticeCard
        title="Risk alerts unavailable"
        message="Fraud alerts could not be loaded. Please retry."
        variant="error"
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Open Alerts"  value={openAlerts}    icon="⚠"  accent="rose"  />
        <StatCard label="Critical"     value={criticalCount} icon="🔴" accent="rose"  />
        <StatCard label="High"         value={highCount}     icon="🟠" accent="amber" />
      </div>

      <DataTable
        columns={columns}
        rows={alerts}
        keyExtractor={(a) => a.id}
        emptyMessage="No active fraud alerts — all clear."
      />

      {pendingAction && (
        <ConfirmationModal
          title={pendingAction.config.label}
          description={pendingAction.config.description}
          confirmLabel={pendingAction.config.confirmLabel}
          variant={pendingAction.config.variant}
          loading={reviewMutation.isPending}
          onConfirm={() =>
            reviewMutation.mutate({
              id: pendingAction.alert.id,
              action: pendingAction.config.action,
            })
          }
          onCancel={() => setPendingAction(null)}
        />
      )}
    </div>
  )
}
