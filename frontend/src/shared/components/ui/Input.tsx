import type { InputHTMLAttributes } from 'react'
import { cn } from '../../../core/utils/cn'

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  hasError?: boolean
}

export function Input({ className, hasError = false, ...props }: InputProps) {
  return (
    <input
      className={cn(
        'min-h-[44px] w-full rounded-md border px-3 py-2 text-sm text-text-primary outline-none transition-all duration-300',
        'bg-white/70 backdrop-blur-sm',
        'border-white/20 hover:border-white/30',
        hasError
          ? 'border-brand-danger focus:border-brand-danger focus:shadow-[0_0_0_3px_rgba(197,48,48,0.1)]'
          : 'border-white/20 focus:border-brand-primary focus:shadow-[0_0_0_3px_rgba(15,76,129,0.1)]',
        className,
      )}
      {...props}
    />
  )
}
