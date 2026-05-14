import { logger } from '../utils/logger'
import type { PollingCallback, PollingConfig, PollingManager, PollingState } from './types'

/**
 * Smart polling manager with exponential backoff
 * 
 * Features:
 * - 45s base interval (battery-conscious)
 * - Exponential backoff on errors
 * - Pause/resume support (for app background/foreground)
 * - Immediate poll trigger
 * - Multiple callback support
 */
export class SmartPollingManager implements PollingManager {
  private state: PollingState = 'idle'
  private intervalId: number | null = null
  private callbacks: Set<PollingCallback> = new Set()
  private currentInterval: number
  private baseInterval: number
  private readonly maxBackoff: number
  private errorCount = 0

  constructor(config: Partial<PollingConfig> = {}) {
    this.baseInterval = config.interval ?? 45000 // 45 seconds
    this.currentInterval = this.baseInterval
    this.maxBackoff = config.maxBackoff ?? 300000 // 5 minutes

    if (config.autoStart) {
      this.start()
    }

    logger.info('[PollingManager] Initialized', {
      baseInterval: this.baseInterval,
      maxBackoff: this.maxBackoff,
      autoStart: config.autoStart,
    })
  }

  start(): void {
    if (this.state === 'running') {
      logger.warn('[PollingManager] Already running')
      return
    }

    this.state = 'running'
    this.scheduleNextPoll()
    logger.info('[PollingManager] Started', { interval: this.currentInterval })
  }

  stop(): void {
    if (this.intervalId !== null) {
      window.clearTimeout(this.intervalId)
      this.intervalId = null
    }

    this.state = 'stopped'
    this.resetBackoff()
    logger.info('[PollingManager] Stopped')
  }

  pause(): void {
    if (this.state !== 'running') {
      return
    }

    if (this.intervalId !== null) {
      window.clearTimeout(this.intervalId)
      this.intervalId = null
    }

    this.state = 'paused'
    logger.info('[PollingManager] Paused')
  }

  resume(): void {
    if (this.state !== 'paused') {
      return
    }

    this.state = 'running'
    // Immediate poll on resume
    this.pollNow()
    logger.info('[PollingManager] Resumed')
  }

  pollNow(): void {
    if (this.state === 'stopped') {
      logger.warn('[PollingManager] Cannot poll - manager is stopped')
      return
    }

    // Cancel scheduled poll
    if (this.intervalId !== null) {
      window.clearTimeout(this.intervalId)
      this.intervalId = null
    }

    // Execute poll immediately
    this.executePoll()

    // Schedule next poll if running
    if (this.state === 'running') {
      this.scheduleNextPoll()
    }
  }

  onPoll(callback: PollingCallback): () => void {
    this.callbacks.add(callback)
    logger.debug('[PollingManager] Callback registered', { totalCallbacks: this.callbacks.size })

    // Return unsubscribe function
    return () => {
      this.callbacks.delete(callback)
      logger.debug('[PollingManager] Callback unregistered', { totalCallbacks: this.callbacks.size })
    }
  }

  getState(): PollingState {
    return this.state
  }

  getInterval(): number {
    return this.currentInterval
  }

  setInterval(interval: number): void {
    this.baseInterval = interval
    this.currentInterval = interval
    logger.info('[PollingManager] Interval updated', { newInterval: interval })

    // Reschedule if running
    if (this.state === 'running' && this.intervalId !== null) {
      window.clearTimeout(this.intervalId)
      this.scheduleNextPoll()
    }
  }

  private scheduleNextPoll(): void {
    this.intervalId = window.setTimeout(() => {
      this.executePoll()
      if (this.state === 'running') {
        this.scheduleNextPoll()
      }
    }, this.currentInterval)
  }

  private async executePoll(): Promise<void> {
    if (this.callbacks.size === 0) {
      logger.debug('[PollingManager] No callbacks registered, skipping poll')
      return
    }

    logger.debug('[PollingManager] Executing poll', { callbackCount: this.callbacks.size })

    try {
      // Execute all callbacks
      const promises = Array.from(this.callbacks).map(async (callback) => {
        try {
          await callback()
        } catch (error) {
          logger.error('[PollingManager] Callback error', { error })
        }
      })

      await Promise.all(promises)

      // Reset backoff on success
      this.resetBackoff()
      logger.debug('[PollingManager] Poll completed successfully')
    } catch (error) {
      logger.error('[PollingManager] Poll failed', { error })
      this.handleError()
    }
  }

  private handleError(): void {
    this.errorCount++

    // Exponential backoff: 45s → 90s → 180s → 300s (max)
    const backoffMultiplier = Math.min(Math.pow(2, this.errorCount - 1), this.maxBackoff / this.baseInterval)
    this.currentInterval = Math.min(this.baseInterval * backoffMultiplier, this.maxBackoff)

    logger.warn('[PollingManager] Error backoff applied', {
      errorCount: this.errorCount,
      newInterval: this.currentInterval,
    })
  }

  private resetBackoff(): void {
    if (this.errorCount > 0) {
      this.errorCount = 0
      this.currentInterval = this.baseInterval
      logger.debug('[PollingManager] Backoff reset')
    }
  }
}

// Singleton instance
let pollingManagerInstance: SmartPollingManager | null = null

/**
 * Get or create the global polling manager instance
 */
export function getPollingManager(): SmartPollingManager {
  if (!pollingManagerInstance) {
    pollingManagerInstance = new SmartPollingManager({
      interval: 45000, // 45 seconds
      maxBackoff: 300000, // 5 minutes
      autoStart: false, // Start manually after app initialization
    })
  }
  return pollingManagerInstance
}
