import type { AuthTokens } from '../platform/storage/types'
import { getTokenStorage } from '../platform/storage'

export function readAccessToken() {
  return getTokenStorage().readAccessToken()
}

export function readRefreshToken() {
  return getTokenStorage().readRefreshToken()
}

export function saveTokens(tokens: AuthTokens) {
  getTokenStorage().saveTokens(tokens)
}

export function clearTokens() {
  getTokenStorage().clearTokens()
}
