import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { 
  AlertTriangle, 
  ArrowRightLeft, 
  ArrowDownLeft, 
  ArrowUpRight, 
  Smartphone, 
  Shield,
  Eye,
  AlertOctagon,
  Ban,
  MessageSquareWarning,
  TrendingUp,
  ChevronRight
} from 'lucide-react'
import { Badge } from '../../../shared/components/ui/Badge'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { ConfirmationModal } from '../../../shared/components/ui/ConfirmationModal'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import { getRiskAlerts, reviewRiskAlert, type RiskAlertAction } from '../../staff/services/staff-service'
import type { FraudAlert as RiskAlert } from '../../staff/types'
import { AlertDetailDrawer } from '../components/AlertDetailDrawer'

type ActionConfig = {
  action: RiskAlertAction
  label: string
  description: string
  confirmLabel: string
  variant: 'danger' | 'warning'
  icon: React.ReactNode
  isPrimary?: boolean
}

const ACTIONS: ActionConfig[] = [
  {
    action: 'DISMISS',
    label: 'Review & Dismiss',
    description: 'Mark this alert as reviewed and dismissed.',
    confirmLabel: 'Dismiss Alert',
    variant: 'warning',
    icon: <Eye className="h-3.5 w-3.5" />,
    isPrimary: true,
  },
  {
    action: 'ESCALATE',
    label: 'Escalate',
    description: 'Escalate this alert to senior staff for review.',
    confirmLabel: 'Escalate to Senior Staff',
    variant: 'warning',
    icon: <TrendingUp className="h-3.5 w-3.5" />,
    isPrimary: true,
  },
  {
    action: 'WARN',
    label: 'Warn User',
    description: 'Send a warning notification to the user associated with this alert.',
    confirmLabel: 'Send Warning',
    variant: 'warning',
    icon: <MessageSquareWarning className="h-3.5 w-3.5" />,
  },
  {
    action: 'FREEZE_ACCOUNT',
    label: 'Freeze Account',
    description: 'Temporarily freeze the associated account. The user will not be able to transact until unfrozen.',
    confirmLabel: 'Freeze Account',
    variant: 'danger',
    icon: <AlertOctagon className="h-3.5 w-3.5" />,
  },
  {
    action: 'BLOCK_ACCOUNT',
    label: 'Block Account',
    description: 'Permanently block the associated account. This action cannot be undone.',
    confirmLabel: 'Block Account Permanently',
    variant: 'danger',
    icon: <Ban className="h-3.5 w-3.5" />,
  },
]

// Alert type configuration - now uses transactionType for better granularity
const getAlertTypeConfig = (alert: RiskAlert) => {
  const alertType = alert.alertType?.toUpperCase() || ''
  const transactionType = alert.transactionType?.toUpperCase() || ''
  
  // For LOGIN alerts
  if (alertType.includes('LOGIN')) {
    return { icon: <Smartphone className="h-4 w-4" />, color: 'text-blue-600', bgColor: 'bg-blue-50', label: 'Login' }
  }
  
  // For TRANSACTION alerts, use the specific transaction type
  if (alertType.includes('TRANSACTION')) {
    if (transactionType.includes('TRANSFER')) {
      return { icon: <ArrowRightLeft className="h-4 w-4" />, color: 'text-orange-600', bgColor: 'bg-orange-50', label: 'Transfer' }
    }
    if (transactionType.includes('WITHDRAW')) {
      return { icon: <ArrowDownLeft className="h-4 w-4" />, color: 'text-red-600', bgColor: 'bg-red-50', label: 'Withdrawal' }
    }
    if (transactionType.includes('DEPOSIT')) {
      return { icon: <ArrowUpRight className="h-4 w-4" />, color: 'text-green-600', bgColor: 'bg-green-50', label: 'Deposit' }
    }
    if (transactionType.includes('QR')) {
      return { icon: <ArrowRightLeft className="h-4 w-4" />, color: 'text-purple-600', bgColor: 'bg-purple-50', label: 'QR Payment' }
    }
    if (transactionType.includes('BILL')) {
      return { icon: <ArrowUpRight className="h-4 w-4" />, color: 'text-amber-600', bgColor: 'bg-amber-50', label: 'Bill Payment' }
    }
    // Generic transaction fallback
    return { icon: <ArrowRightLeft className="h-4 w-4" />, color: 'text-gray-600', bgColor: 'bg-gray-50', label: 'Transaction' }
  }
  
  return { icon: <AlertTriangle className="h-4 w-4" />, color: 'text-gray-600', bgColor: 'bg-gray-50', label: alertType.replace(/_/g, ' ') }
}

// Severity configuration
const getSeverityConfig = (severity: string) => {
  switch (severity) {
    case 'CRITICAL':
      return { color: 'bg-red-100 text-red-800 border-red-200', label: 'Critical' }
    case 'HIGH':
      return { color: 'bg-orange-100 text-orange-800 border-orange-200', label: 'High' }
    case 'MEDIUM':
      return { color: 'bg-amber-100 text-amber-800 border-amber-200', label: 'Medium' }
    case 'LOW':
      return { color: 'bg-blue-100 text-blue-800 border-blue-200', label: 'Low' }
    default:
      return { color: 'bg-gray-100 text-gray-800 border-gray-200', label: severity }
  }
}

// Risk score label and color
const getRiskScoreLabel = (score: number) => {
  if (score >= 75) return { label: 'Dangerous', color: 'text-red-600', bgColor: 'bg-red-50', barColor: 'bg-red-500' }
  if (score >= 50) return { label: 'Suspicious', color: 'text-orange-600', bgColor: 'bg-orange-50', barColor: 'bg-orange-500' }
  return { label: 'Safe', color: 'text-green-600', bgColor: 'bg-green-50', barColor: 'bg-green-500' }
}

// Format relative time
const getRelativeTime = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  return date.toLocaleDateString()
}


export function RiskAlertsPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [pendingAction, setPendingAction] = useState<{
    alert: RiskAlert
    config: ActionConfig
  } | null>(null)
  const [selectedAlert, setSelectedAlert] = useState<RiskAlert | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

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
  const openAlerts = alerts.filter((a) => a.status === 'OPEN').length
  const criticalCount = alerts.filter((a) => a.severity === 'CRITICAL').length
  const highCount = alerts.filter((a) => a.severity === 'HIGH').length

  if (alertsQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 w-full rounded-xl" />
        <Skeleton className="h-96 w-full rounded-xl" />
      </div>
    )
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

  // Empty state
  if (alerts.length === 0) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center rounded-xl border-2 border-dashed border-border-primary bg-surface-secondary p-12">
        <div className="mb-4 rounded-full bg-green-50 p-4">
          <Shield className="h-12 w-12 text-green-600" />
        </div>
        <h3 className="mb-2 text-lg font-semibold text-text-primary">No Active Risk Alerts</h3>
        <p className="text-sm text-text-tertiary">All systems operating normally. No fraud alerts detected.</p>
      </div>
    )
  }

  const handleAlertClick = (alert: RiskAlert) => {
    setSelectedAlert(alert)
    setIsDrawerOpen(true)
  }

  const handleCloseDrawer = () => {
    setIsDrawerOpen(false)
    setTimeout(() => setSelectedAlert(null), 300)
  }

  return (
    <>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">Risk Alerts</h1>
            <p className="mt-1 text-sm text-text-tertiary">
              Monitor and investigate fraud detection alerts
            </p>
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-border-primary bg-surface-primary p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-text-tertiary">Open Alerts</p>
              <p className="mt-1 text-3xl font-bold text-text-primary">{openAlerts}</p>
            </div>
            <div className="rounded-lg bg-rose-50 p-3">
              <AlertTriangle className="h-6 w-6 text-rose-600" />
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border-primary bg-surface-primary p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-text-tertiary">Critical</p>
              <p className="mt-1 text-3xl font-bold text-red-600">{criticalCount}</p>
            </div>
            <div className="rounded-lg bg-red-50 p-3">
              <AlertOctagon className="h-6 w-6 text-red-600" />
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border-primary bg-surface-primary p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-text-tertiary">High Priority</p>
              <p className="mt-1 text-3xl font-bold text-orange-600">{highCount}</p>
            </div>
            <div className="rounded-lg bg-orange-50 p-3">
              <AlertTriangle className="h-6 w-6 text-orange-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Level 1: Clean Summary Table */}
      <div className="overflow-hidden rounded-xl border border-border-primary bg-surface-primary shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-border-primary bg-surface-secondary">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  Alert Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  Severity
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  Risk Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-primary">
              {alerts.map((alert) => {
                const typeConfig = getAlertTypeConfig(alert)
                const severityConfig = getSeverityConfig(alert.severity)
                const score = alert.combinedScore ?? parseFloat(alert.riskScore) ?? 0
                const scoreConfig = getRiskScoreLabel(score)

                return (
                  <tr
                    key={alert.id}
                    onClick={() => handleAlertClick(alert)}
                    className="group cursor-pointer transition-colors hover:bg-surface-secondary"
                  >
                    {/* Alert Type */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className={`rounded-lg ${typeConfig.bgColor} p-2`}>
                          <div className={typeConfig.color}>{typeConfig.icon}</div>
                        </div>
                        <div>
                          <p className="font-semibold text-text-primary">{typeConfig.label}</p>
                          {alert.autoActionTaken && (
                            <span className="mt-0.5 inline-block rounded bg-purple-100 px-1.5 py-0.5 text-xs font-medium text-purple-700">
                              Auto-actioned
                            </span>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* User */}
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-text-primary">
                        {alert.userName || 'Unknown'}
                      </p>
                      <p className="text-xs text-text-tertiary">
                        {alert.userPhone || alert.accountNumber || '—'}
                      </p>
                    </td>

                    {/* Severity */}
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-semibold ${severityConfig.color}`}
                      >
                        {severityConfig.label}
                      </span>
                    </td>

                    {/* Risk Score */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xl font-bold text-text-primary">{score}</span>
                        <div className="h-8 w-1 rounded-full bg-surface-tertiary">
                          <div
                            className={`w-full rounded-full transition-all ${scoreConfig.barColor}`}
                            style={{ height: `${Math.min(score, 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* Time */}
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-text-secondary">
                        {getRelativeTime(alert.createdAt)}
                      </p>
                      <p className="text-xs text-text-tertiary">
                        {new Date(alert.createdAt).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </td>

                    {/* Status */}
                    <td className="px-6 py-4">
                      <Badge
                        variant={
                          alert.status === 'OPEN'
                            ? 'warning'
                            : alert.status === 'DISMISSED'
                            ? 'info'
                            : 'success'
                        }
                      >
                        {alert.status}
                      </Badge>
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        {alert.status === 'OPEN' && (
                          <>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                setPendingAction({
                                  alert,
                                  config: ACTIONS.find((a) => a.action === 'DISMISS')!,
                                })
                              }}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-border-primary bg-surface-primary px-3 py-1.5 text-sm font-medium text-text-primary transition-colors hover:bg-surface-secondary"
                            >
                              <Eye className="h-3.5 w-3.5" />
                              Dismiss
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handleAlertClick(alert)
                              }}
                              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                            >
                              Investigate
                              <ChevronRight className="h-3.5 w-3.5" />
                            </button>
                          </>
                        )}
                        {alert.status !== 'OPEN' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleAlertClick(alert)
                            }}
                            className="text-sm text-blue-600 hover:text-blue-700"
                          >
                            View Details
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation modal */}
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

    {/* Level 2: Detail Investigation Drawer */}
    <AlertDetailDrawer
      alert={selectedAlert}
      isOpen={isDrawerOpen}
      onClose={handleCloseDrawer}
    />
  </>
  )
}
