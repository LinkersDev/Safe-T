import { NavLink } from 'react-router-dom'
import { cn } from '../../../core/utils/cn'
import { useAuthSession } from '../../../domains/security/hooks/useAuthSession'
import { getNavItems } from '../../../core/navigation/nav-items'
import type { RoleCode } from '../../../core/state/auth-state'

const ROLE_LABELS: Partial<Record<RoleCode, string>> = {
  CUSTOMER: 'Customer',
  ADMIN: 'Administrator',
  TELLER: 'Teller',
  TELLER_ADMIN: 'Senior Teller',
  RISK_OFFICER: 'Risk Officer',
  CUSTOMER_SERVICE: 'Customer Service',
}

const ROLE_ACCENT: Partial<Record<RoleCode, string>> = {
  CUSTOMER: 'bg-indigo-500',
  ADMIN: 'bg-violet-500',
  TELLER: 'bg-amber-500',
  TELLER_ADMIN: 'bg-amber-600',
  RISK_OFFICER: 'bg-rose-500',
  CUSTOMER_SERVICE: 'bg-emerald-500',
}

type SidebarProps = {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const session = useAuthSession()
  const role = session.user?.role ?? null
  const navItems = getNavItems(role, session.permissions)

  const accentClass = role ? (ROLE_ACCENT[role] ?? 'bg-slate-500') : 'bg-slate-500'
  const roleLabel = role ? (ROLE_LABELS[role] ?? role) : ''

  const mainItems = navItems.filter((i) => i.group === 'main')
  const supportItems = navItems.filter((i) => i.group === 'support')
  const ungroupedItems = navItems.filter((i) => !i.group)

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-20 bg-black/50 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-30 flex w-60 flex-col bg-slate-900 transition-transform duration-200',
          'lg:static lg:translate-x-0 lg:z-auto',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-slate-700/50 px-5">
          <div className={cn('flex h-8 w-8 items-center justify-center rounded-lg text-white text-sm font-bold', accentClass)}>
            S
          </div>
          <span className="text-lg font-bold text-white">SafeT</span>
        </div>

        {/* User info */}
        <div className="border-b border-slate-700/50 px-5 py-4">
          <p className="truncate text-sm font-semibold text-white">{session.user?.fullName ?? '—'}</p>
          <div className="mt-1 flex items-center gap-2">
            <span className={cn('inline-block h-2 w-2 rounded-full', accentClass)} />
            <span className="text-xs text-slate-400">{roleLabel}</span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {/* Main items */}
          {mainItems.length > 0 && (
            <>
              {mainItems.map((item) => (
                <NavItem key={item.path} item={item} onClick={onClose} />
              ))}
            </>
          )}

          {/* Ungrouped (staff) items */}
          {ungroupedItems.length > 0 && (
            <>
              {ungroupedItems.map((item) => (
                <NavItem key={item.path} item={item} onClick={onClose} />
              ))}
            </>
          )}

          {/* Support group */}
          {supportItems.length > 0 && (
            <div className="pt-4">
              <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                Support
              </p>
              {supportItems.map((item) => (
                <NavItem key={item.path} item={item} onClick={onClose} />
              ))}
            </div>
          )}
        </nav>

        {/* Bottom accent bar */}
        <div className={cn('h-1 w-full', accentClass)} />
      </aside>
    </>
  )
}

function NavItem({ item, onClick }: { item: import('../../../core/navigation/nav-items').NavItem; onClick: () => void }) {
  return (
    <NavLink
      to={item.path}
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-white/10 text-white'
            : 'text-slate-400 hover:bg-white/5 hover:text-slate-200',
        )
      }
    >
      <span className="text-base leading-none">{item.icon}</span>
      <span>{item.label}</span>
    </NavLink>
  )
}
