type StatusNoticeCardProps = {
  title: string
  message: string
  variant?: 'error' | 'warning' | 'info'
}

const STYLE: Record<NonNullable<StatusNoticeCardProps['variant']>, string> = {
  error: 'border-rose-200 bg-rose-50 text-rose-700',
  warning: 'border-amber-200 bg-amber-50 text-amber-700',
  info: 'border-slate-200 bg-slate-50 text-slate-700',
}

export function StatusNoticeCard({ title, message, variant = 'info' }: StatusNoticeCardProps) {
  return (
    <div className={`rounded-xl border px-4 py-3 ${STYLE[variant]}`}>
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-0.5 text-xs">{message}</p>
    </div>
  )
}
