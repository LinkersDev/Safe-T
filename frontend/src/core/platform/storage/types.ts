export type AuthTokens = {
  accessToken: string
  refreshToken: string
}

export interface TokenStorage {
  readAccessToken(): string | null
  readRefreshToken(): string | null
  saveTokens(tokens: AuthTokens): void
  clearTokens(): void
}
