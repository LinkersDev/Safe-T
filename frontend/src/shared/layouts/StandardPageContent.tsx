import type { ReactNode } from 'react'
import { cn } from '../../core/utils/cn'

type StandardPageContentProps = {
  children: ReactNode
  className?: string
  showHeader?: boolean
  headerContent?: ReactNode
}

/**
 * StandardPageContent wraps IonContent to provide consistent padding and spacing
 * across authenticated and other standard pages, following the design system scale.
 *
 * - Mobile: 16px horizontal padding, 24px vertical padding
 * - Desktop (sm and above): 24px horizontal padding
 * - Elevation: e0 (no shadow, flat border)
 */
export function StandardPageContent({
  children,
  className,
  showHeader = false,
  headerContent,
}: StandardPageContentProps) {
  return (
    <main
      className={cn(
        'w-full px-4 py-6 sm:px-6',
        'bg-surface-primary',
        'min-h-screen',
        className,
      )}
    >
      {showHeader && headerContent && (
        <header className="mb-6">{headerContent}</header>
      )}
      {children}
    </main>
  )
}
