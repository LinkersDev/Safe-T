import { useSyncExternalStore } from 'react'
import { saveTokensAsync, clearTokensAsync } from '../../../core/auth/token-service'
import { decodeJwtPayload, isJwtExpired } from '../../../core/auth/jwt'
import { getRolePermissions } from '../../../core/permissions/role-permissions'
import {
  clearSessionState,
  getSessionState,
  setSessionState,
  subscribeSessionState,
} from '../../../core/state/auth-state'
import type { LoginResponse, MockAuthLoginResponse } from '../types'
import type { RoleCode } from '../../../core/state/auth-state'


export function useAuthSession() {
  return useSyncExternalStore(subscribeSessionState, getSessionState, getSessionState)
}

export async function startSession(response: LoginResponse): Promise<void> {
  await saveTokensAsync({
    accessToken: response.access,
    refreshToken: response.refresh,
  })

  const user = {
    id: response.user.id,
    fullName: response.user.full_name,
    phoneNumber: response.user.phone_number,
    status: response.user.status,
    role: response.user.role,
    kycStatus: response.user.kyc_status ?? 'NOT_SUBMITTED',
  }

  setSessionState({
    isAuthenticated: true,
    mockMode: false,
    user,
    permissions:
      response.permissions && response.permissions.length > 0
        ? response.permissions
        : getRolePermissions(user.role),
  })
}

export async function startMockSession(response: MockAuthLoginResponse): Promise<void> {
  await saveTokensAsync({
    accessToken: response.session.access_token,
    refreshToken: 'mock-refresh-token',
  })

  const roleCode =
    response.user.role === 'admin'
      ? 'ADMIN'
      : response.user.role === 'teller'
        ? 'TELLER'
        : 'CUSTOMER'

  setSessionState({
    isAuthenticated: true,
    mockMode: true,
    user: {
      id: response.user.id,
      fullName: response.user.fullName,
      role: roleCode,
      kycStatus: response.user.kycStatus,
      status: 'ACTIVE',
    },
    permissions: getRolePermissions(roleCode),
  })
}

export async function endSession(): Promise<void> {
  await clearTokensAsync()
  clearSessionState()
}

export function hasStoredSession() {
  try {
    return Boolean(window.localStorage.getItem('safet.access.token'))
  } catch {
    return false
  }
}

export function ensureSessionHydratedFromToken() {
  const state = getSessionState()
  if (state.isAuthenticated) {
    return
  }

  let token: string | null = null
  try {
    token = window.localStorage.getItem('safet.access.token')
  } catch {
    return
  }
  if (!token) {
    return
  }

  const payload = decodeJwtPayload(token)
  if (!payload || isJwtExpired(payload)) {
    clearTokensAsync().catch(() => {})
    clearSessionState()
    return
  }

  const role = (payload.role ?? null) as RoleCode | null
  const status = typeof payload.status === 'string' ? payload.status : undefined
  const kycStatus = typeof payload.kyc_status === 'string' ? payload.kyc_status : undefined
  const fullName = typeof payload.full_name === 'string' ? payload.full_name : 'User'
  const phoneNumber = typeof payload.phone_number === 'string' ? payload.phone_number : undefined
  const userId = (payload.user_id ?? payload.sub ?? 'unknown') as string | number

  setSessionState({
    isAuthenticated: true,
    mockMode: false,
    user: {
      id: userId,
      fullName,
      phoneNumber,
      role,
      status: status as any,
      kycStatus: kycStatus as any,
    },
    permissions: getRolePermissions(role),
  })
}
