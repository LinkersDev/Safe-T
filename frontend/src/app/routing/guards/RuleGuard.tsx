import { Navigate } from 'react-router-dom'
import { ROUTE_PATHS } from '../paths'
import { evaluateRuleGate } from '../../../core/rules/rule-gates'
import { useAuthSession } from '../../../domains/security/hooks/useAuthSession'
import type { RuleGate } from '../../../core/rules/rule-gates'
import type { ReactNode } from 'react'

type RuleGuardProps = {
  gate: RuleGate
  children: ReactNode
}

export function RuleGuard({ gate, children }: RuleGuardProps) {
  useAuthSession()

  if (!evaluateRuleGate(gate)) {
    return <Navigate to={ROUTE_PATHS.profile} replace />
  }

  return <>{children}</>
}
