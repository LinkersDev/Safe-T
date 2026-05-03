import type { ReactNode } from 'react'
import { cn } from '../../../core/utils/cn'

type BadgeVariant = 'info' | 'success' | 'warning' | 'danger'

type BadgeProps = {
  children: ReactNode
  variant?: BadgeVariant
}

const variantClassName: Record<BadgeVariant, string> = {
  info: 'bg-[#EEF4FF] text-brand-info',
  success: 'bg-[#EAF7F0] text-brand-success',
  warning: 'bg-[#FFF7E8] text-brand-warning',
  danger: 'bg-[#FDECEC] text-brand-danger',
}

export function Badge({ children, variant = 'info' }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex min-h-6 items-center rounded-full px-2.5 py-1 text-xs font-semibold tracking-wide',
        variantClassName[variant],
      )}
    >
      {children}
    </span>
  )
}
