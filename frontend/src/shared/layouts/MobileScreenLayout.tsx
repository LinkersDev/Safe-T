import type { ReactNode } from 'react'

type MobileScreenLayoutProps = {
  title: string
  subtitle?: string
  children: ReactNode
}

export function MobileScreenLayout({ title, subtitle, children }: MobileScreenLayoutProps) {
  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-4 py-6 sm:px-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-text-secondary">{subtitle}</p> : null}
      </header>
      {children}
    </main>
  )
}
