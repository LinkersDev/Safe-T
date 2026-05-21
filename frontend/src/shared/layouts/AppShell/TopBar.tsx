import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { cn } from '../../../core/utils/cn'
import { useAuthSession, endSession } from '../../../domains/security/hooks/useAuthSession'
import { isStaffRole } from '../../../core/permissions/capabilities'
import { getNotificationCount } from '../../../domains/support/services/support-service'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import type { RoleCode } from '../../../core/state/auth-state'

const ROLE_BADGE: Partial<Record<RoleCode, { label: string; className: string }>> = {
  CUSTOMER:        { label: 'Customer',      className: 'bg-indigo-100 text-indigo-700'  },
  ADMIN:           { label: 'Admin',         className: 'bg-violet-100 text-violet-700'  },
  TELLER:          { label: 'Teller',        className: 'bg-amber-100  text-amber-700'   },
  TELLER_ADMIN:    { label: 'Sr. Teller',    className: 'bg-amber-100  text-amber-700'   },
  RISK_OFFICER:    { label: 'Risk Officer',  className: 'bg-rose-100   text-rose-700'    },
  CUSTOMER_SERVICE:{ label: 'Support Agent', className: 'bg-emerald-100 text-emerald-700'},
}

type TopBarProps = {
  title?: string
  onMenuClick: () => void
}

export function TopBar({ title, onMenuClick }: TopBarProps) {
  const session = useAuthSession()
  const navigate = useNavigate()
  const role = session.user?.role ?? null
  const badge = role ? (ROLE_BADGE[role] ?? null) : null

  const { data: unreadCount } = useQuery({
    queryKey: ['notification-count'],
    queryFn: getNotificationCount,
    refetchInterval: 60_000,
    enabled: session.isAuthenticated,
    staleTime: 30_000,
  })

  function handleLogout() {
    endSession()
    navigate(ROUTE_PATHS.login, { replace: true })
  }

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-surface-primary px-4 sm:px-6">
      {/* Left: hamburger + page title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-surface-secondary lg:hidden"
          aria-label="Open menu"
        >
          <span className="text-lg">☰</span>
        </button>
        {title && (
          <h1 className="text-base font-semibold text-text-primary sm:text-lg">{title}</h1>
        )}
      </div>

      {/* Right: bell + role badge + user + logout */}
      <div className="flex items-center gap-3">
        {/* Notification bell */}
        <button
          onClick={() => navigate(isStaffRole(role) ? ROUTE_PATHS.staff : ROUTE_PATHS.notifications)}
          className="relative flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-surface-secondary transition-colors"
          aria-label="Notifications"
        >
          <span className="text-lg">🔔</span>
          {unreadCount != null && unreadCount > 0 && (
            <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>

        {badge && (
          <span className={cn('hidden rounded-full px-2.5 py-1 text-xs font-semibold sm:inline-flex', badge.className)}>
            {badge.label}
          </span>
        )}
        <span className="hidden max-w-32 truncate text-sm font-medium text-text-secondary sm:block">
          {session.user?.fullName}
        </span>
        <button
          onClick={handleLogout}
          className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-text-secondary hover:bg-surface-secondary transition-colors"
        >
          Sign out
        </button>
      </div>
    </header>
  )
}
