import { App, type AppState } from '@capacitor/app'
import { isWeb } from './platform-detector'
import { logger } from '../utils/logger'

/**
 * App state listener callback
 */
export type AppStateCallback = (isActive: boolean) => void

/**
 * App state manager for handling foreground/background transitions
 * 
 * Features:
 * - Listen to app state changes (foreground/background)
 * - Notify callbacks when app becomes active/inactive
 * - Works on mobile (Capacitor) and web (Page Visibility API)
 */
class AppStateManager {
  private callbacks: Set<AppStateCallback> = new Set()
  private isActive = true
  private initialized = false

  /**
   * Initialize app state listeners
   */
  init(): void {
    if (this.initialized) {
      logger.warn('[AppState] Already initialized')
      return
    }

    if (isWeb()) {
      this.initWebListeners()
    } else {
      this.initCapacitorListeners()
    }

    this.initialized = true
    logger.info('[AppState] Initialized', { platform: isWeb() ? 'web' : 'mobile' })
  }

  /**
   * Register a callback to be called when app state changes
   * @returns Unsubscribe function
   */
  onStateChange(callback: AppStateCallback): () => void {
    this.callbacks.add(callback)
    logger.debug('[AppState] Callback registered', { totalCallbacks: this.callbacks.size })

    // Immediately call with current state
    callback(this.isActive)

    // Return unsubscribe function
    return () => {
      this.callbacks.delete(callback)
      logger.debug('[AppState] Callback unregistered', { totalCallbacks: this.callbacks.size })
    }
  }

  /**
   * Get current app state
   */
  getIsActive(): boolean {
    return this.isActive
  }

  /**
   * Initialize Capacitor app state listeners (mobile)
   */
  private initCapacitorListeners(): void {
    App.addListener('appStateChange', (state: AppState) => {
      const wasActive = this.isActive
      this.isActive = state.isActive

      if (wasActive !== this.isActive) {
        logger.info('[AppState] State changed', {
          isActive: this.isActive,
          state: this.isActive ? 'foreground' : 'background',
        })
        this.notifyCallbacks()
      }
    })
  }

  /**
   * Initialize web page visibility listeners (web)
   */
  private initWebListeners(): void {
    document.addEventListener('visibilitychange', () => {
      const wasActive = this.isActive
      this.isActive = document.visibilityState === 'visible'

      if (wasActive !== this.isActive) {
        logger.info('[AppState] Visibility changed', {
          isActive: this.isActive,
          visibilityState: document.visibilityState,
        })
        this.notifyCallbacks()
      }
    })
  }

  /**
   * Notify all registered callbacks
   */
  private notifyCallbacks(): void {
    this.callbacks.forEach((callback) => {
      try {
        callback(this.isActive)
      } catch (error) {
        logger.error('[AppState] Callback error', { error })
      }
    })
  }
}

// Singleton instance
const appStateManager = new AppStateManager()

/**
 * Get the global app state manager instance
 */
export function getAppStateManager(): AppStateManager {
  return appStateManager
}

/**
 * Initialize app state monitoring
 * Should be called once during app initialization
 */
export function initAppState(): void {
  appStateManager.init()
}
