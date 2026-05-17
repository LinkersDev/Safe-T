import axios from 'axios'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { clearTokensAsync, readAccessTokenAsync, readRefreshTokenAsync, saveTokensAsync } from '../auth/token-service'
import { getDeviceIdentity } from '../platform/device'
import { clearSessionState } from '../state/auth-state'
import { emitSessionExpired } from '../events/session-events'

const API_BASE_URL = import.meta.env.DEV
  ? 'http://localhost:8000'
  : (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000')

type PendingRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean }

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use(async (config) => {
  const accessToken = await readAccessTokenAsync()
  const deviceIdentity = getDeviceIdentity()

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }

  const deviceId = await deviceIdentity.getDeviceId()
  const deviceName = await deviceIdentity.getDeviceName()
  
  config.headers['X-Device-Id'] = deviceId
  config.headers['X-Device-Name'] = deviceName

  return config
})

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken() {
  const refreshToken = await readRefreshTokenAsync()
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

    await saveTokensAsync({ accessToken: nextAccess, refreshToken: nextRefresh })
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

    const requestUrl = requestConfig?.url ?? ''
    const isAuthEndpoint = requestUrl.includes('/auth/login') || requestUrl.includes('/auth/token')
    if (status !== 401 || !requestConfig || requestConfig._retry || isAuthEndpoint) {
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
      await clearTokensAsync()
      clearSessionState()
      emitSessionExpired()
      return Promise.reject(error)
    }

    requestConfig.headers.Authorization = `Bearer ${refreshedAccessToken}`
    return apiClient(requestConfig)
  },
)

export { apiClient }
