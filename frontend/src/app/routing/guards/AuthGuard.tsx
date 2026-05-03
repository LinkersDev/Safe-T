import { Navigate, useLocation } from 'react-router-dom'
import { ROUTE_PATHS } from '../paths'
import {
  ensureSessionHydratedFromToken,
  hasStoredSession,
  useAuthSession,
} from '../../../domains/security/hooks/useAuthSession'
import { getSessionState } from '../../../core/state/auth-state'
import type { ReactNode } from 'react'

type AuthGuardProps = {
  children: ReactNode
}

export function AuthGuard({ children }: AuthGuardProps) {
  const session = useAuthSession()
  const location = useLocation()

  if (!session.isAuthenticated && hasStoredSession()) {
    ensureSessionHydratedFromToken()
  }

  const nextSession = getSessionState()

  if (!nextSession.isAuthenticated && !hasStoredSession()) {
    return <Navigate to={ROUTE_PATHS.login} replace state={{ from: location.pathname }} />
  }

  return <>{children}</>
}
