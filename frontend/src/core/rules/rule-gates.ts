import { getSessionState } from '../state/auth-state'

export type RuleGate = 'KYC_APPROVED'

export function evaluateRuleGate(gate: RuleGate): boolean {
  const { user } = getSessionState()

  if (!user) {
    return false
  }

  switch (gate) {
    case 'KYC_APPROVED':
      return user.kycStatus === 'APPROVED'
    default:
      return false
  }
}
