import type { FraudAlert } from '../../staff/types'

export type RiskExplanation = {
  title: string
  description: string
  factors: string[]
  recommendation: string
}

export function generateRiskExplanation(alert: FraudAlert): RiskExplanation {
  const alertType = alert.alertType?.toUpperCase() || ''
  const transactionType = alert.transactionType?.toUpperCase() || ''
  const severity = alert.severity?.toUpperCase() || ''
  const score = alert.combinedScore ?? parseFloat(alert.riskScore) ?? 0
  const mlProb = alert.mlFraudProbability ?? 0
  const ruleScore = alert.ruleBasedScore ?? 0
  const rules = alert.rulesTriggered || []
  
  const factors: string[] = []
  let title = ''
  let description = ''
  let recommendation = ''
  
  // Determine primary risk factor
  if (alertType.includes('TRANSACTION')) {
    // Transaction-based alerts
    const amount = alert.transactionAmount ? parseFloat(alert.transactionAmount) : 0
    const currency = alert.transactionCurrency || 'USD'
    
    if (transactionType.includes('TRANSFER')) {
      title = 'Suspicious Transfer Detected'
      description = `A ${currency} ${amount.toLocaleString('en-US', { minimumFractionDigits: 2 })} transfer triggered fraud detection rules.`
    } else if (transactionType.includes('WITHDRAW')) {
      title = 'Suspicious Withdrawal Detected'
      description = `A ${currency} ${amount.toLocaleString('en-US', { minimumFractionDigits: 2 })} withdrawal triggered fraud detection rules.`
    } else if (transactionType.includes('DEPOSIT')) {
      title = 'Suspicious Deposit Detected'
      description = `A ${currency} ${amount.toLocaleString('en-US', { minimumFractionDigits: 2 })} deposit triggered fraud detection rules.`
    } else {
      title = 'Suspicious Transaction Detected'
      description = `A ${currency} ${amount.toLocaleString('en-US', { minimumFractionDigits: 2 })} transaction triggered fraud detection rules.`
    }
    
    // Add transaction-specific factors
    if (amount >= 10000) {
      factors.push('High-value transaction (≥ $10,000)')
    } else if (amount >= 5000) {
      factors.push('Elevated transaction amount (≥ $5,000)')
    }
    
    if (rules.some(r => r.toLowerCase().includes('velocity'))) {
      factors.push('Multiple rapid transactions detected')
    }
    
    if (rules.some(r => r.toLowerCase().includes('abnormal') || r.toLowerCase().includes('hour'))) {
      factors.push('Transaction occurred during abnormal hours (midnight–5am)')
    }
    
    if (rules.some(r => r.toLowerCase().includes('device'))) {
      factors.push('Transaction from new or unrecognized device')
    }
    
    if (rules.some(r => r.toLowerCase().includes('ip') || r.toLowerCase().includes('location'))) {
      factors.push('Transaction from unusual location or IP address')
    }
    
  } else if (alertType.includes('LOGIN')) {
    // Login-based alerts
    title = 'Suspicious Login Activity'
    description = `A login attempt triggered fraud detection rules.`
    
    if (alert.loginLocation) {
      description += ` Location: ${alert.loginLocation}.`
    }
    
    if (rules.some(r => r.toLowerCase().includes('device'))) {
      factors.push('Login from new or unrecognized device')
    }
    
    if (rules.some(r => r.toLowerCase().includes('country') || r.toLowerCase().includes('location'))) {
      factors.push('Login from unusual geographic location')
    }
    
    if (rules.some(r => r.toLowerCase().includes('fail'))) {
      factors.push('Multiple failed login attempts detected')
    }
    
    if (alert.loginIpAddress) {
      factors.push(`IP address: ${alert.loginIpAddress}`)
    }
  }
  
  // Add ML-based factors
  if (mlProb >= 0.7) {
    factors.push('AI model indicates high fraud probability (≥ 70%)')
  } else if (mlProb >= 0.5) {
    factors.push('AI model indicates elevated fraud probability (≥ 50%)')
  } else if (mlProb >= 0.3) {
    factors.push('AI model indicates moderate fraud probability (≥ 30%)')
  }
  
  // Add rule-based factors
  if (ruleScore >= 75) {
    factors.push('Critical risk score from rule-based analysis')
  } else if (ruleScore >= 50) {
    factors.push('High risk score from rule-based analysis')
  }
  
  // Generate recommendation based on severity
  if (severity === 'CRITICAL') {
    recommendation = 'IMMEDIATE ACTION REQUIRED: Review and take action immediately. Consider freezing account if fraud is confirmed.'
    if (alert.autoActionTaken) {
      recommendation = 'Account has been automatically frozen. Review urgently and take appropriate action.'
    }
  } else if (severity === 'HIGH') {
    recommendation = 'HIGH PRIORITY: Review within 1 hour. Contact user if suspicious activity is confirmed.'
  } else if (severity === 'MEDIUM') {
    recommendation = 'MODERATE PRIORITY: Review within 24 hours. Monitor for additional suspicious activity.'
  } else {
    recommendation = 'LOW PRIORITY: Review when convenient. May be a false positive.'
  }
  
  // If no specific factors identified, add generic ones
  if (factors.length === 0) {
    factors.push('Fraud detection rules triggered')
    if (score > 0) {
      factors.push(`Risk score: ${score}`)
    }
  }
  
  return {
    title,
    description,
    factors,
    recommendation,
  }
}

export function getRiskScoreInterpretation(score: number): {
  level: string
  color: string
  description: string
} {
  if (score >= 75) {
    return {
      level: 'CRITICAL',
      color: 'text-red-600',
      description: 'Extremely high fraud probability. Immediate investigation required.',
    }
  }
  if (score >= 50) {
    return {
      level: 'HIGH',
      color: 'text-orange-600',
      description: 'High fraud probability. Prompt investigation recommended.',
    }
  }
  if (score >= 25) {
    return {
      level: 'MEDIUM',
      color: 'text-amber-600',
      description: 'Moderate fraud probability. Review and monitor activity.',
    }
  }
  return {
    level: 'LOW',
    color: 'text-green-600',
    description: 'Low fraud probability. Routine monitoring sufficient.',
  }
}

export function getMLConfidenceLevel(probability: number | null): {
  level: string
  color: string
  description: string
} {
  if (probability === null) {
    return {
      level: 'N/A',
      color: 'text-gray-600',
      description: 'ML model prediction not available',
    }
  }
  
  if (probability >= 0.8) {
    return {
      level: 'VERY HIGH',
      color: 'text-red-600',
      description: 'AI model is highly confident this is fraudulent',
    }
  }
  if (probability >= 0.6) {
    return {
      level: 'HIGH',
      color: 'text-orange-600',
      description: 'AI model indicates strong fraud signals',
    }
  }
  if (probability >= 0.4) {
    return {
      level: 'MODERATE',
      color: 'text-amber-600',
      description: 'AI model detects some fraud indicators',
    }
  }
  if (probability >= 0.2) {
    return {
      level: 'LOW',
      color: 'text-blue-600',
      description: 'AI model detects minimal fraud signals',
    }
  }
  return {
    level: 'VERY LOW',
    color: 'text-green-600',
    description: 'AI model indicates legitimate activity',
  }
}
