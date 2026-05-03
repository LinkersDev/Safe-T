import type { ButtonHTMLAttributes } from 'react'
import { cn } from '../../../core/utils/cn'

type ButtonVariant = 'primary' | 'secondary' | 'danger'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  loading?: boolean
}

const baseClassName =
  'inline-flex min-h-[44px] items-center justify-center rounded-md px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60'

const variantClassNames: Record<ButtonVariant, string> = {
  primary: 'bg-brand-primary text-white hover:bg-[#0C3E69]',
  secondary: 'bg-surface-secondary text-text-primary hover:bg-[#E6EBF2]',
  danger: 'bg-brand-danger text-white hover:bg-[#AE2A2A]',
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
