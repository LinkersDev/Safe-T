import type { InputHTMLAttributes } from 'react'
import { cn } from '../../../core/utils/cn'

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  hasError?: boolean
}

export function Input({ className, hasError = false, ...props }: InputProps) {
  return (
    <input
      className={cn(
        'min-h-[44px] w-full rounded-md border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none transition-colors',
        hasError
          ? 'border-brand-danger focus:border-brand-danger'
          : 'border-border focus:border-brand-primary',
        className,
      )}
      {...props}
    />
  )
}
