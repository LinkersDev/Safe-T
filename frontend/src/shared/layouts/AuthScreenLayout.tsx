import type { ReactNode } from 'react'
import { cn } from '../../core/utils/cn'

type AuthScreenLayoutProps = {
  title: string
  subtitle?: string
  children: ReactNode
  isLoading?: boolean
  logo?: ReactNode
  className?: string
}

/**
 * AuthScreenLayout is a full-screen authentication form container.
 * Features:
 * - Centered Card (max-w-md on desktop, full width on mobile with gutters)
 * - Optional logo slot at the top of the card
 * - Title and optional subtitle header
 * - Elevation e1 (shadow-sm) on card
 * - Single scroll container, no double scroll
 * - Mobile-first responsive design
 */
export function AuthScreenLayout({
  title,
  subtitle,
  children,
  isLoading = false,
  logo,
  className,
}: AuthScreenLayoutProps) {
  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-4 py-6 sm:px-6 flex items-center justify-center">
      <div className="animate-fade-in-up w-full max-w-md">
        <div
          className={cn(
            'rounded-2xl p-8 space-y-6',
            'glassmorphic glass-hover',
            className,
          )}
        >
          {/* Logo slot */}
          {logo && (
            <div className="flex justify-center mb-6">
              {logo}
            </div>
          )}

          {/* Title and Subtitle */}
          <div className="text-center mb-8 animate-slide-in-down">
            <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-brand-primary to-brand-secondary bg-clip-text text-transparent">
              {title}
            </h1>
            {subtitle && (
              <p className="mt-3 text-sm font-medium text-text-secondary">{subtitle}</p>
            )}
          </div>

          {/* Form Content */}
          <div className={cn('space-y-4', isLoading ? 'opacity-60 pointer-events-none' : '')}>
            {children}
          </div>
        </div>
      </div>
    </main>
  )
}
