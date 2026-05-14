/**
 * Real-time polling types and interfaces
 */

export type PollingState = 'idle' | 'running' | 'paused' | 'stopped'

export type PollingCallback = () => void | Promise<void>

export interface PollingConfig {
  /**
   * Base polling interval in milliseconds
   * @default 45000 (45 seconds)
   */
  interval: number

  /**
   * Maximum backoff interval in milliseconds (for error recovery)
   * @default 300000 (5 minutes)
   */
  maxBackoff: number

  /**
   * Whether to start polling immediately
   * @default false
   */
  autoStart: boolean
}

export interface PollingManager {
  /**
   * Start polling with the configured interval
   */
  start(): void

  /**
   * Stop polling completely
   */
  stop(): void

  /**
   * Pause polling (can be resumed)
   */
  pause(): void

  /**
   * Resume polling after pause
   */
  resume(): void

  /**
   * Trigger an immediate poll (resets interval)
   */
  pollNow(): void

  /**
   * Register a callback to be called on each poll
   */
  onPoll(callback: PollingCallback): () => void

  /**
   * Get current polling state
   */
  getState(): PollingState

  /**
   * Get current interval
   */
  getInterval(): number

  /**
   * Update polling interval
   */
  setInterval(interval: number): void
}
