import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { useState, type ReactNode } from 'react'
import { ToastProvider } from '../../shared/components/ui/Toast'
import { SessionExpiredBanner } from '../../shared/components/SessionExpiredBanner'

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

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ToastProvider>
          <SessionExpiredBanner />
          {children}
        </ToastProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
