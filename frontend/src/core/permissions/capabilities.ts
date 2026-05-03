import { getSessionState } from '../state/auth-state'
import type { RoleCode } from '../state/auth-state'

export function hasRole(allowedRoles: RoleCode[]) {
  const role = getSessionState().user?.role
  return role ? allowedRoles.includes(role) : false
}

export function hasPermission(requiredPermission: string) {
  return getSessionState().permissions.includes(requiredPermission)
}
