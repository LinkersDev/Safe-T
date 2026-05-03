import type { TokenStorage } from './types'
import { WebTokenStorage } from './web-token-storage'

let tokenStorage: TokenStorage = new WebTokenStorage()

export function getTokenStorage() {
  return tokenStorage
}

export function setTokenStorage(storage: TokenStorage) {
  tokenStorage = storage
}
