import { Navigate } from 'react-router-dom'
import { ROUTE_PATHS } from '../paths'
import { hasRole } from '../../../core/permissions/capabilities'
import { useAuthSession } from '../../../domains/security/hooks/useAuthSession'
import type { RoleCode } from '../../../core/state/auth-state'
import type { ReactNode } from 'react'

type RoleGuardProps = {
  allowedRoles: RoleCode[]
  children: ReactNode
}

export function RoleGuard({ allowedRoles, children }: RoleGuardProps) {
  useAuthSession()

  if (!hasRole(allowedRoles)) {
    return <Navigate to={ROUTE_PATHS.forbidden} replace />
  }

  return <>{children}</>
}
