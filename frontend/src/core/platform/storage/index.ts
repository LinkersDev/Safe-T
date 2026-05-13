import type { TokenStorage } from './types'
import { WebTokenStorage } from './web-token-storage'
import { CapacitorTokenStorage } from './capacitor-token-storage'
import { isMobile } from '../platform-detector'

let tokenStorage: TokenStorage = isMobile() 
  ? new CapacitorTokenStorage() 
  : new WebTokenStorage()

export function getTokenStorage(): TokenStorage {
  return tokenStorage
}

export function setTokenStorage(storage: TokenStorage): void {
  tokenStorage = storage
}
