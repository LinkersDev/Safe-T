import { getSessionState } from '../state/auth-state'
import type { RoleCode } from '../state/auth-state'

const STAFF_ROLE_CODES: RoleCode[] = ['ADMIN', 'TELLER', 'TELLER_ADMIN', 'CUSTOMER_SERVICE', 'RISK_OFFICER']

export function hasRole(allowedRoles: RoleCode[]) {
  const role = getSessionState().user?.role
  return role ? allowedRoles.includes(role) : false
}

export function hasPermission(requiredPermission: string) {
  return getSessionState().permissions.includes(requiredPermission)
}

export function isStaffRole(role: RoleCode | null | undefined): boolean {
  return role ? STAFF_ROLE_CODES.includes(role) : false
}
