import axios from 'axios'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { clearTokens, readAccessToken, readRefreshToken, saveTokens } from '../auth/token-service'
import { getDeviceIdentity } from '../platform/device'
import { clearSessionState } from '../state/auth-state'
import { emitSessionExpired } from '../events/session-events'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

type PendingRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean }

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const accessToken = readAccessToken()
  const deviceIdentity = getDeviceIdentity()

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }

  config.headers['X-Device-Id'] = deviceIdentity.getDeviceId()
  config.headers['X-Device-Name'] = deviceIdentity.getDeviceName()

  return config
})

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken() {
  const refreshToken = readRefreshToken()
  if (!refreshToken) {
    return null
  }

  try {
    const response = await axios.post(`${API_BASE_URL}/api/auth/token/refresh/`, {
      refresh: refreshToken,
    })

    const nextAccess = response.data?.access as string | undefined
    const nextRefresh = (response.data?.refresh as string | undefined) ?? refreshToken

    if (!nextAccess) {
      return null
    }

    saveTokens({ accessToken: nextAccess, refreshToken: nextRefresh })
    return nextAccess
  } catch {
    return null
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const status = error.response?.status
    const requestConfig = error.config as PendingRequestConfig | undefined

    if (status !== 401 || !requestConfig || requestConfig._retry) {
      return Promise.reject(error)
    }

    requestConfig._retry = true

    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null
      })
    }

    const refreshedAccessToken = await refreshPromise

    if (!refreshedAccessToken) {
      clearTokens()
      clearSessionState()
      emitSessionExpired()
      return Promise.reject(error)
    }

    requestConfig.headers = requestConfig.headers ?? {}
    requestConfig.headers.Authorization = `Bearer ${refreshedAccessToken}`
    return apiClient(requestConfig)
  },
)

export { apiClient }
