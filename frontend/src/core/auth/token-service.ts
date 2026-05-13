import type { AuthTokens } from '../platform/storage/types'
import { getTokenStorage } from '../platform/storage'

// LEGACY SYNC API - deprecated, use async versions
/** @deprecated */
export function readAccessToken(): string | null {
  console.warn('[token-service] Sync API deprecated - use readAccessTokenAsync')
  return null
}

/** @deprecated */
export function readRefreshToken(): string | null {
  console.warn('[token-service] Sync API deprecated - use readRefreshTokenAsync')
  return null
}

/** @deprecated */
export function saveTokens(tokens: AuthTokens): void {
  saveTokensAsync(tokens).catch(err => console.error('Token save failed:', err))
}

/** @deprecated */
export function clearTokens(): void {
  clearTokensAsync().catch(err => console.error('Token clear failed:', err))
}

// MODERN ASYNC API
export async function readAccessTokenAsync(): Promise<string | null> {
  return await getTokenStorage().readAccessToken()
}

export async function readRefreshTokenAsync(): Promise<string | null> {
  return await getTokenStorage().readRefreshToken()
}

export async function saveTokensAsync(tokens: AuthTokens): Promise<void> {
  await getTokenStorage().saveTokens(tokens)
}

export async function clearTokensAsync(): Promise<void> {
  await getTokenStorage().clearTokens()
}
