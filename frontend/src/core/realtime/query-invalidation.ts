import type { QueryClient } from '@tanstack/react-query'
import { logger } from '../utils/logger'

/**
 * Query invalidation manager for real-time updates
 * 
 * Handles targeted invalidation of React Query caches
 * when polling detects new data.
 */
export class QueryInvalidationManager {
  private queryClient: QueryClient | null = null

  /**
   * Set the React Query client instance
   */
  setQueryClient(client: QueryClient): void {
    this.queryClient = client
    logger.info('[QueryInvalidation] Query client registered')
  }

  /**
   * Invalidate account/balance queries
   * Called when polling detects potential balance changes
   */
  async invalidateAccounts(): Promise<void> {
    if (!this.queryClient) {
      logger.warn('[QueryInvalidation] No query client registered')
      return
    }

    try {
      await this.queryClient.invalidateQueries({
        queryKey: ['accounts'],
      })
      logger.debug('[QueryInvalidation] Accounts invalidated')
    } catch (error) {
      logger.error('[QueryInvalidation] Failed to invalidate accounts', { error })
    }
  }

  /**
   * Invalidate transaction/ledger queries
   * Called when polling detects new transactions
   */
  async invalidateTransactions(): Promise<void> {
    if (!this.queryClient) {
      logger.warn('[QueryInvalidation] No query client registered')
      return
    }

    try {
      await this.queryClient.invalidateQueries({
        queryKey: ['ledger'],
      })
      logger.debug('[QueryInvalidation] Transactions invalidated')
    } catch (error) {
      logger.error('[QueryInvalidation] Failed to invalidate transactions', { error })
    }
  }

  /**
   * Invalidate both accounts and transactions
   * Called during polling to refresh dashboard data
   */
  async invalidateAll(): Promise<void> {
    await Promise.all([
      this.invalidateAccounts(),
      this.invalidateTransactions(),
    ])
    logger.debug('[QueryInvalidation] All queries invalidated')
  }

  /**
   * Force immediate refetch of accounts
   */
  async refetchAccounts(): Promise<void> {
    if (!this.queryClient) {
      logger.warn('[QueryInvalidation] No query client registered')
      return
    }

    try {
      await this.queryClient.refetchQueries({
        queryKey: ['accounts'],
      })
      logger.debug('[QueryInvalidation] Accounts refetched')
    } catch (error) {
      logger.error('[QueryInvalidation] Failed to refetch accounts', { error })
    }
  }

  /**
   * Force immediate refetch of transactions
   */
  async refetchTransactions(): Promise<void> {
    if (!this.queryClient) {
      logger.warn('[QueryInvalidation] No query client registered')
      return
    }

    try {
      await this.queryClient.refetchQueries({
        queryKey: ['ledger'],
      })
      logger.debug('[QueryInvalidation] Transactions refetched')
    } catch (error) {
      logger.error('[QueryInvalidation] Failed to refetch transactions', { error })
    }
  }
}

// Singleton instance
const queryInvalidationManager = new QueryInvalidationManager()

/**
 * Get the global query invalidation manager
 */
export function getQueryInvalidationManager(): QueryInvalidationManager {
  return queryInvalidationManager
}
