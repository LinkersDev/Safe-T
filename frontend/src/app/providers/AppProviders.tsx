import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import { useState, useEffect, type ReactNode } from 'react'
import { ToastProvider } from '../../shared/components/ui/Toast'
import { SessionExpiredBanner } from '../../shared/components/SessionExpiredBanner'
import { isMobile } from '../../core/platform/platform-detector'
import { getPollingManager } from '../../core/realtime/polling-manager'
import { getQueryInvalidationManager } from '../../core/realtime/query-invalidation'
import { getAppStateManager, initAppState } from '../../core/platform/app-state'
import { logger } from '../../core/utils/logger'

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
            staleTime: isMobile() ? 60_000 : 30_000, // Longer stale time on mobile
            gcTime: 5 * 60_000,
            retry: 1,
          },
          mutations: {
            retry: 0,
          },
        },
      }),
  )

  // Initialize real-time polling and app state management
  useEffect(() => {
    logger.info('[AppProviders] Initializing real-time features')

    // Register query client with invalidation manager
    const invalidationManager = getQueryInvalidationManager()
    invalidationManager.setQueryClient(queryClient)

    // Initialize app state monitoring
    initAppState()
    const appStateManager = getAppStateManager()

    // Get polling manager
    const pollingManager = getPollingManager()

    // Register polling callback to invalidate queries
    const unsubscribePoll = pollingManager.onPoll(async () => {
      logger.debug('[AppProviders] Polling tick - invalidating queries')
      await invalidationManager.invalidateAll()
    })

    // Register app state callback to pause/resume polling
    const unsubscribeAppState = appStateManager.onStateChange((isActive) => {
      if (isActive) {
        logger.info('[AppProviders] App became active - resuming polling')
        pollingManager.resume()
      } else {
        logger.info('[AppProviders] App became inactive - pausing polling')
        pollingManager.pause()
      }
    })

    // Start polling (will be paused if app is in background)
    pollingManager.start()
    logger.info('[AppProviders] Polling started')

    // Cleanup on unmount
    return () => {
      logger.info('[AppProviders] Cleaning up real-time features')
      unsubscribePoll()
      unsubscribeAppState()
      pollingManager.stop()
    }
  }, [queryClient])

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
