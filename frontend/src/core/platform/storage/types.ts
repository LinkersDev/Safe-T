export type AuthTokens = {
  accessToken: string
  refreshToken: string
}

export interface TokenStorage {
  readAccessToken(): Promise<string | null>
  readRefreshToken(): Promise<string | null>
  saveTokens(tokens: AuthTokens): Promise<void>
  clearTokens(): Promise<void>
}
