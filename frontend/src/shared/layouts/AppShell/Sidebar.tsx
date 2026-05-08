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
  CUSTOMER: 'bg-blue-500',
  ADMIN: 'bg-blue-500',
  TELLER: 'bg-amber-500',
  TELLER_ADMIN: 'bg-amber-500',
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
          'fixed inset-y-0 left-0 z-30 flex w-60 flex-col transition-transform duration-200',
          'lg:static lg:translate-x-0 lg:z-auto',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
        style={{ backgroundColor: 'var(--sidebar-bg)' }}
      >
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-slate-700/30 px-5">
          <div className={cn('flex h-8 w-8 items-center justify-center rounded-lg text-white text-sm font-bold', accentClass)}>
            S
          </div>
          <span className="text-lg font-bold text-white">SafeT</span>
        </div>

        {/* User info */}
        <div className="border-b border-slate-700/30 px-5 py-4">
          <p className="truncate text-sm font-semibold text-white">{session.user?.fullName ?? '—'}</p>
          <div className="mt-1.5 flex items-center gap-2">
            <span className={cn('inline-block h-2 w-2 rounded-full', accentClass)} />
            <span className="text-xs" style={{ color: 'var(--sidebar-text)' }}>{roleLabel}</span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
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
            <div className="pt-6">
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--sidebar-text)' }}>
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
          'sidebar-item flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium relative overflow-hidden',
          isActive
            ? 'text-white font-semibold'
            : 'hover:text-white',
        )
      }
      style={({ isActive }) => ({
        backgroundColor: isActive ? 'var(--sidebar-active-bg)' : undefined,
        color: isActive ? 'var(--sidebar-text-active)' : 'var(--sidebar-text)',
        transition: 'var(--transition-fast)',
      })}
      onMouseEnter={(e) => {
        if (!e.currentTarget.classList.contains('active')) {
          e.currentTarget.style.backgroundColor = 'var(--sidebar-hover-bg)';
        }
      }}
      onMouseLeave={(e) => {
        if (!e.currentTarget.classList.contains('active')) {
          e.currentTarget.style.backgroundColor = 'transparent';
        }
      }}
    >
      {({ isActive }) => (
        <>
          {/* Active left border indicator */}
          {isActive && (
            <div 
              className="absolute left-0 top-0 bottom-0 w-[3px] rounded-r-full"
              style={{ backgroundColor: 'var(--sidebar-active-border)' }}
            />
          )}
          <span className="flex items-center justify-center w-5 h-5">
            <item.icon size={18} strokeWidth={2} />
          </span>
          <span>{item.label}</span>
        </>
      )}
    </NavLink>
  )
}
