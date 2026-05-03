export type RoleCode =
  | 'CUSTOMER'
  | 'ADMIN'
  | 'TELLER'
  | 'TELLER_ADMIN'
  | 'MERCHANT_CUSTOMER'
  | 'CUSTOMER_SERVICE'
  | 'RISK_OFFICER'

export type SessionUser = {
  id: number | string
  fullName: string
  phoneNumber?: string
  status?: 'PENDING_VERIFICATION' | 'ACTIVE' | 'REJECTED' | 'BLOCKED'
  role: RoleCode | null
  kycStatus?: 'NOT_SUBMITTED' | 'PENDING' | 'APPROVED' | 'REJECTED'
}

export type SessionState = {
  isAuthenticated: boolean
  mockMode: boolean
  user: SessionUser | null
  permissions: string[]
}

let sessionState: SessionState = {
  isAuthenticated: false,
  mockMode: false,
  user: null,
  permissions: [],
}

const listeners = new Set<() => void>()

export function getSessionState(): SessionState {
  return sessionState
}

export function setSessionState(next: SessionState) {
  sessionState = next
  listeners.forEach((listener) => listener())
}

export function updateSessionState(next: Partial<SessionState>) {
  setSessionState({
    ...sessionState,
    ...next,
  })
}

export function clearSessionState() {
  setSessionState({
    isAuthenticated: false,
    mockMode: false,
    user: null,
    permissions: [],
  })
}

export function subscribeSessionState(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
