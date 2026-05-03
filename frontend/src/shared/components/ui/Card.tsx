import type { ComponentPropsWithoutRef, ElementType, ReactNode } from 'react'
import { cn } from '../../../core/utils/cn'

type CardProps<T extends ElementType = 'section'> = {
  as?: T
  children: ReactNode
  className?: string
} & Omit<ComponentPropsWithoutRef<T>, 'as' | 'children' | 'className'>

export function Card<T extends ElementType = 'section'>({
  as,
  children,
  className,
  ...props
}: CardProps<T>) {
  const Component = as ?? 'section'

  return (
    <Component
      className={cn('rounded-lg border border-border bg-surface-primary p-4 shadow-sm', className)}
      {...props}
    >
      {children}
    </Component>
  )
}
