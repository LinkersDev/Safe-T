import type { AuthTokens, TokenStorage } from './types'

const ACCESS_KEY = 'safet.access.token'
const REFRESH_KEY = 'safet.refresh.token'

export class WebTokenStorage implements TokenStorage {
  readAccessToken() {
    return window.sessionStorage.getItem(ACCESS_KEY)
  }

  readRefreshToken() {
    return window.sessionStorage.getItem(REFRESH_KEY)
  }

  saveTokens(tokens: AuthTokens) {
    window.sessionStorage.setItem(ACCESS_KEY, tokens.accessToken)
    window.sessionStorage.setItem(REFRESH_KEY, tokens.refreshToken)
  }

  clearTokens() {
    window.sessionStorage.removeItem(ACCESS_KEY)
    window.sessionStorage.removeItem(REFRESH_KEY)
  }
}
