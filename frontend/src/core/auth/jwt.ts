type JwtPayload = Record<string, unknown>

function base64UrlDecode(input: string) {
  const normalized = input.replace(/-/g, '+').replace(/_/g, '/')
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
  return atob(padded)
}

export function decodeJwtPayload(token: string): JwtPayload | null {
  const parts = token.split('.')
  if (parts.length < 2) return null

  try {
    const json = base64UrlDecode(parts[1])
    return JSON.parse(json) as JwtPayload
  } catch {
    return null
  }
}

export function isJwtExpired(payload: JwtPayload, nowSeconds = Math.floor(Date.now() / 1000)) {
  const exp = payload.exp
  if (typeof exp !== 'number') return false
  return nowSeconds >= exp
}

