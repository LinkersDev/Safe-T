import { useNavigate } from 'react-router-dom'
import { Badge } from '../../../shared/components/ui/Badge'
import { useAuthSession } from '../hooks/useAuthSession'
import { ROUTE_PATHS } from '../../../app/routing/paths'

const KYC_VARIANT: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
  APPROVED: 'success',
  PENDING: 'warning',
  UNDER_REVIEW: 'info',
  REJECTED: 'danger',
  NOT_SUBMITTED: 'info',
}

export function ProfilePage() {
  const session = useAuthSession()
  const navigate = useNavigate()
  const user = session.user

  if (!user) return null

  return (
    <div className="mx-auto max-w-xl space-y-6">
      {/* Avatar + name card */}
      <div className="rounded-2xl border border-border bg-surface-primary p-6">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-2xl font-bold text-indigo-700">
            {user.fullName?.[0]?.toUpperCase() ?? '?'}
          </div>
          <div>
            <h2 className="text-xl font-bold text-text-primary">{user.fullName}</h2>
            <p className="text-sm text-text-secondary">{user.phoneNumber ?? '—'}</p>
            <p className="mt-1 text-xs text-text-tertiary capitalize">
              Role: <span className="font-semibold">{user.role}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Account status */}
      <div className="rounded-2xl border border-border bg-surface-primary divide-y divide-border overflow-hidden">
        <SectionRow label="Account Status">
          <Badge variant={user.status === 'ACTIVE' ? 'success' : 'danger'}>
            {user.status}
          </Badge>
        </SectionRow>
        <SectionRow label="KYC Status">
          <Badge variant={KYC_VARIANT[user.kycStatus ?? 'NOT_SUBMITTED'] ?? 'info'}>
            {user.kycStatus ?? 'NOT_SUBMITTED'}
          </Badge>
        </SectionRow>
        <SectionRow label="User ID">
          <span className="font-mono text-xs text-text-secondary">{user.id}</span>
        </SectionRow>
      </div>

      {/* Actions */}
      <div className="space-y-3">
        <ActionButton
          icon="🔑"
          label="Change Password"
          description="Update your account password"
          onClick={() =>
            navigate(ROUTE_PATHS.resetPassword, {
              state: user.phoneNumber ? { phoneNumber: user.phoneNumber } : undefined,
            })
          }
        />
        <ActionButton
          icon="✉"
          label="Support Tickets"
          description="View or create support requests"
          onClick={() => navigate(ROUTE_PATHS.tickets)}
        />
        <ActionButton
          icon="🔔"
          label="Notifications"
          description="View your notification history"
          onClick={() => navigate(ROUTE_PATHS.notifications)}
        />
      </div>
    </div>
  )
}

function SectionRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-5 py-3.5">
      <span className="text-sm text-text-secondary">{label}</span>
      <span className="text-sm font-medium">{children}</span>
    </div>
  )
}

function ActionButton({
  icon,
  label,
  description,
  onClick,
}: {
  icon: string
  label: string
  description: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-4 rounded-xl border border-border bg-surface-primary px-5 py-4 text-left hover:bg-surface-secondary transition-colors"
    >
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-lg">
        {icon}
      </span>
      <div className="flex-1">
        <p className="text-sm font-semibold text-text-primary">{label}</p>
        <p className="text-xs text-text-secondary">{description}</p>
      </div>
      <span className="text-text-tertiary">›</span>
    </button>
  )
}
