import type { ReactNode } from 'react'
import { cn } from '../../../core/utils/cn'

type StatCardProps = {
  label: string
  value: string | number
  icon?: ReactNode
  trend?: string
  trendUp?: boolean
  accent?: 'indigo' | 'violet' | 'amber' | 'rose' | 'emerald' | 'blue' | 'slate'
  className?: string
}

const accentMap: Record<NonNullable<StatCardProps['accent']>, { icon: string; badge: string }> = {
  indigo: { icon: 'bg-indigo-100 text-indigo-600', badge: 'text-indigo-600' },
  violet: { icon: 'bg-violet-100 text-violet-600', badge: 'text-violet-600' },
  amber:  { icon: 'bg-amber-100  text-amber-600',  badge: 'text-amber-600'  },
  rose:   { icon: 'bg-rose-100   text-rose-600',   badge: 'text-rose-600'   },
  emerald:{ icon: 'bg-emerald-100 text-emerald-600',badge: 'text-emerald-600'},
  blue:   { icon: 'bg-blue-100   text-blue-600',   badge: 'text-blue-600'   },
  slate:  { icon: 'bg-slate-100  text-slate-600',  badge: 'text-slate-600'  },
}

export function StatCard({ label, value, icon, trend, trendUp, accent = 'slate', className }: StatCardProps) {
  const colors = accentMap[accent]
  return (
    <div className={cn('rounded-xl border border-border bg-surface-primary p-5 shadow-sm', className)}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-text-tertiary">{label}</p>
          <p className="mt-2 text-3xl font-bold text-text-primary">{value}</p>
          {trend ? (
            <p className={cn('mt-1 text-xs font-medium', trendUp ? 'text-emerald-600' : 'text-rose-600')}>
              {trendUp ? '▲' : '▼'} {trend}
            </p>
          ) : null}
        </div>
        {icon ? (
          <div className={cn('flex h-10 w-10 items-center justify-center rounded-lg text-lg', colors.icon)}>
            {icon}
          </div>
        ) : null}
      </div>
    </div>
  )
}
