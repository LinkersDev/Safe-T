import { IonRefresher, IonRefresherContent } from '@ionic/react'
import type { RefresherEventDetail } from '@ionic/react'
import { logger } from '../../core/utils/logger'

type PullToRefreshProps = {
  onRefresh: () => Promise<void>
  disabled?: boolean
}

/**
 * Pull-to-refresh component for mobile
 * 
 * Uses Ionic's IonRefresher for native-like pull-to-refresh gesture
 */
export function PullToRefresh({ onRefresh, disabled = false }: PullToRefreshProps) {
  const handleRefresh = async (event: CustomEvent<RefresherEventDetail>) => {
    logger.info('[PullToRefresh] Refresh triggered')

    try {
      await onRefresh()
      logger.info('[PullToRefresh] Refresh completed')
    } catch (error) {
      logger.error('[PullToRefresh] Refresh failed', { error })
    } finally {
      event.detail.complete()
    }
  }

  if (disabled) {
    return null
  }

  return (
    <IonRefresher slot="fixed" onIonRefresh={handleRefresh}>
      <IonRefresherContent
        pullingText="Pull to refresh..."
        refreshingText="Updating..."
      />
    </IonRefresher>
  )
}
