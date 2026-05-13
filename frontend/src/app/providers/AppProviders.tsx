import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import { useState, type ReactNode } from 'react'
import { ToastProvider } from '../../shared/components/ui/Toast'
import { SessionExpiredBanner } from '../../shared/components/SessionExpiredBanner'
import { isMobile } from '../../core/platform/platform-detector'

type AppProvidersProps = {
  children: ReactNode
}

export function AppProviders({ children }: AppProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            refetchOnReconnect: true,
            staleTime: 30_000,
            gcTime: 5 * 60_000,
            retry: 1,
          },
          mutations: {
            retry: 0,
          },
        },
      }),
  )

  const Router = isMobile() ? HashRouter : BrowserRouter

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <ToastProvider>
          <SessionExpiredBanner />
          {children}
        </ToastProvider>
      </Router>
    </QueryClientProvider>
  )
}
