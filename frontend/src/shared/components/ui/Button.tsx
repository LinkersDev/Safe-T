import type { ButtonHTMLAttributes } from 'react'
import { cn } from '../../../core/utils/cn'

type ButtonVariant = 'primary' | 'secondary' | 'danger'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  loading?: boolean
}

const baseClassName =
  'inline-flex min-h-[44px] items-center justify-center rounded-md px-4 py-2 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-60 hover:shadow-lg'

const variantClassNames: Record<ButtonVariant, string> = {
  primary: 'bg-gradient-to-br from-brand-primary via-[#0d4475] to-brand-secondary text-white hover:-translate-y-1 hover:shadow-xl active:translate-y-0',
  secondary: 'bg-surface-secondary text-text-primary hover:bg-[#E6EBF2] hover:-translate-y-1 transition-all',
  danger: 'bg-gradient-to-br from-brand-danger to-[#a02424] text-white hover:-translate-y-1 hover:shadow-xl active:translate-y-0',
}

export function Button({
  variant = 'primary',
  loading = false,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(baseClassName, variantClassNames[variant], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? 'Loading...' : children}
    </button>
  )
}
