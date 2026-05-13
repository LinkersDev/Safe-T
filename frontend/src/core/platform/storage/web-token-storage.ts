import type { AuthTokens, TokenStorage } from './types'

const ACCESS_KEY = 'safet.access.token'
const REFRESH_KEY = 'safet.refresh.token'

export class WebTokenStorage implements TokenStorage {
  async readAccessToken(): Promise<string | null> {
    return window.sessionStorage.getItem(ACCESS_KEY)
  }

  async readRefreshToken(): Promise<string | null> {
    return window.sessionStorage.getItem(REFRESH_KEY)
  }

  async saveTokens(tokens: AuthTokens): Promise<void> {
    window.sessionStorage.setItem(ACCESS_KEY, tokens.accessToken)
    window.sessionStorage.setItem(REFRESH_KEY, tokens.refreshToken)
  }

  async clearTokens(): Promise<void> {
    window.sessionStorage.removeItem(ACCESS_KEY)
    window.sessionStorage.removeItem(REFRESH_KEY)
  }
}
