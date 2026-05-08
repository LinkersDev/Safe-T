import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '../../../core/utils/cn'

type StatCardProps = {
  label: string
  value: string | number
  icon?: LucideIcon | ReactNode
  trend?: string
  trendUp?: boolean
  accent?: 'blue' | 'green' | 'amber' | 'rose' | 'slate' | 'emerald' | 'indigo' | 'violet'
  className?: string
}

const accentMap: Record<NonNullable<StatCardProps['accent']>, { icon: string; border: string; iconBg: string }> = {
  blue:    { icon: 'text-blue-600',   border: 'border-l-blue-500',   iconBg: 'bg-blue-50' },
  green:   { icon: 'text-emerald-600', border: 'border-l-emerald-500', iconBg: 'bg-emerald-50' },
  emerald: { icon: 'text-emerald-600', border: 'border-l-emerald-500', iconBg: 'bg-emerald-50' },
  amber:   { icon: 'text-amber-600',  border: 'border-l-amber-500',  iconBg: 'bg-amber-50' },
  rose:    { icon: 'text-rose-600',   border: 'border-l-rose-500',   iconBg: 'bg-rose-50' },
  slate:   { icon: 'text-slate-600',  border: 'border-l-slate-400',  iconBg: 'bg-slate-50' },
  indigo:  { icon: 'text-indigo-600', border: 'border-l-indigo-500', iconBg: 'bg-indigo-50' },
  violet:  { icon: 'text-violet-600', border: 'border-l-violet-500', iconBg: 'bg-violet-50' },
}

export function StatCard({ label, value, icon, trend, trendUp, accent = 'slate', className }: StatCardProps) {
  const colors = accentMap[accent]
  const isStringIcon = typeof icon === 'string'
  const IconComp = isStringIcon ? null : (icon as LucideIcon | undefined)
  return (
    <div 
      className={cn(
        'card-hover rounded-xl border border-[#E2E8F0] bg-white p-5 relative overflow-hidden',
        colors.border,
        className
      )}
      style={{ 
        boxShadow: '0 4px 20px rgba(10, 37, 64, 0.08)',
        borderLeftWidth: '3px',
        transition: 'all 0.2s ease',
      }}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{value}</p>
          {trend ? (
            <p className={cn('mt-1 text-xs font-medium', trendUp ? 'text-emerald-600' : 'text-rose-600')}>
              {trendUp ? '↑' : '↓'} {trend}
            </p>
          ) : null}
        </div>
        {icon ? (
          <div className={cn('flex h-10 w-10 items-center justify-center rounded-lg text-lg', colors.iconBg, colors.icon)}>
            {isStringIcon ? (
              <span>{icon}</span>
            ) : IconComp ? (
              <IconComp size={20} strokeWidth={2} />
            ) : (
              icon as ReactNode
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}
