import { X, AlertTriangle, Brain, CreditCard, Smartphone, MapPin, Clock, Shield, TrendingUp, Activity } from 'lucide-react'
import type { FraudAlert } from '../../staff/types'
import { generateRiskExplanation, getRiskScoreInterpretation, getMLConfidenceLevel } from '../utils/risk-explanation'

type AlertDetailDrawerProps = {
  alert: FraudAlert | null
  isOpen: boolean
  onClose: () => void
}

export function AlertDetailDrawer({ alert, isOpen, onClose }: AlertDetailDrawerProps) {
  if (!isOpen || !alert) return null

  const explanation = generateRiskExplanation(alert)
  const score = alert.combinedScore ?? parseFloat(alert.riskScore) ?? 0
  const scoreInterpretation = getRiskScoreInterpretation(score)
  const mlConfidence = getMLConfidenceLevel(alert.mlFraudProbability)

  const isTransaction = alert.alertType?.toUpperCase().includes('TRANSACTION')
  const isLogin = alert.alertType?.toUpperCase().includes('LOGIN')

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-2xl overflow-y-auto bg-surface-primary shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 z-10 border-b border-border-primary bg-surface-primary px-6 py-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-red-50 p-2">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-text-primary">Alert Investigation</h2>
                  <p className="text-sm text-text-tertiary">Alert ID: #{alert.id}</p>
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-text-tertiary transition-colors hover:bg-surface-secondary hover:text-text-primary"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="space-y-6 p-6">
          {/* Risk Explanation Section */}
          <section className="rounded-lg border border-border-primary bg-surface-secondary p-5">
            <div className="mb-4 flex items-start gap-3">
              <div className="rounded-lg bg-amber-50 p-2">
                <Shield className="h-5 w-5 text-amber-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-text-primary">{explanation.title}</h3>
                <p className="mt-1 text-sm text-text-secondary">{explanation.description}</p>
              </div>
            </div>

            {/* Risk Factors */}
            <div className="mt-4 space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                Risk Factors Detected
              </p>
              <ul className="space-y-2">
                {explanation.factors.map((factor, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-text-secondary">
                    <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-amber-500" />
                    {factor}
                  </li>
                ))}
              </ul>
            </div>

            {/* Recommendation */}
            <div className="mt-4 rounded-lg bg-amber-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-amber-900">
                Recommendation
              </p>
              <p className="mt-1 text-sm font-medium text-amber-800">{explanation.recommendation}</p>
            </div>
          </section>

          {/* AI / ML Intelligence Section */}
          <section className="rounded-lg border border-border-primary bg-surface-secondary p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-lg bg-purple-50 p-2">
                <Brain className="h-5 w-5 text-purple-600" />
              </div>
              <h3 className="text-lg font-semibold text-text-primary">AI / ML Intelligence</h3>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {/* Combined Risk Score */}
              <div className="rounded-lg bg-surface-primary p-4">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-text-tertiary" />
                  <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                    Combined Risk Score
                  </p>
                </div>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="font-mono text-3xl font-bold text-text-primary">{score}</span>
                  <span className={`text-sm font-semibold ${scoreInterpretation.color}`}>
                    {scoreInterpretation.level}
                  </span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-tertiary">
                  <div
                    className={`h-full transition-all ${
                      score >= 75
                        ? 'bg-red-500'
                        : score >= 50
                        ? 'bg-orange-500'
                        : score >= 25
                        ? 'bg-amber-500'
                        : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(score, 100)}%` }}
                  />
                </div>
                <p className="mt-2 text-xs text-text-tertiary">{scoreInterpretation.description}</p>
              </div>

              {/* ML Fraud Probability */}
              <div className="rounded-lg bg-surface-primary p-4">
                <div className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-text-tertiary" />
                  <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                    ML Fraud Probability
                  </p>
                </div>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="font-mono text-3xl font-bold text-text-primary">
                    {alert.mlFraudProbability !== null
                      ? `${(alert.mlFraudProbability * 100).toFixed(1)}%`
                      : 'N/A'}
                  </span>
                  <span className={`text-sm font-semibold ${mlConfidence.color}`}>
                    {mlConfidence.level}
                  </span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-tertiary">
                  <div
                    className={`h-full transition-all ${
                      (alert.mlFraudProbability ?? 0) >= 0.8
                        ? 'bg-red-500'
                        : (alert.mlFraudProbability ?? 0) >= 0.6
                        ? 'bg-orange-500'
                        : (alert.mlFraudProbability ?? 0) >= 0.4
                        ? 'bg-amber-500'
                        : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min((alert.mlFraudProbability ?? 0) * 100, 100)}%` }}
                  />
                </div>
                <p className="mt-2 text-xs text-text-tertiary">{mlConfidence.description}</p>
              </div>

              {/* Rule-Based Score */}
              <div className="rounded-lg bg-surface-primary p-4">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-text-tertiary" />
                  <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                    Rule-Based Score
                  </p>
                </div>
                <div className="mt-2">
                  <span className="font-mono text-3xl font-bold text-text-primary">
                    {alert.ruleBasedScore ?? 0}
                  </span>
                </div>
                <p className="mt-2 text-xs text-text-tertiary">
                  Score from predefined fraud detection rules
                </p>
              </div>

              {/* Scoring Breakdown */}
              <div className="rounded-lg bg-surface-primary p-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-text-tertiary" />
                  <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                    Scoring Breakdown
                  </p>
                </div>
                <div className="mt-2 space-y-1 text-xs text-text-secondary">
                  <div className="flex justify-between">
                    <span>ML Model (60%)</span>
                    <span className="font-mono font-semibold">
                      {alert.mlFraudProbability !== null
                        ? Math.round((alert.mlFraudProbability * 100 * 0.6))
                        : 0}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Rules (40%)</span>
                    <span className="font-mono font-semibold">
                      {Math.round((alert.ruleBasedScore ?? 0) * 0.4)}
                    </span>
                  </div>
                  <div className="mt-2 border-t border-border-primary pt-1" />
                  <div className="flex justify-between font-semibold">
                    <span>Combined Score</span>
                    <span className="font-mono">{score}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Rules Triggered */}
            {alert.rulesTriggered && alert.rulesTriggered.length > 0 && (
              <div className="mt-4 rounded-lg bg-surface-primary p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  Rules Triggered
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {alert.rulesTriggered.map((rule, idx) => (
                    <span
                      key={idx}
                      className="rounded-md bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800"
                    >
                      {rule}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* Transaction Context (if applicable) */}
          {isTransaction && (
            <section className="rounded-lg border border-border-primary bg-surface-secondary p-5">
              <div className="mb-4 flex items-center gap-3">
                <div className="rounded-lg bg-blue-50 p-2">
                  <CreditCard className="h-5 w-5 text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold text-text-primary">Transaction Context</h3>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                {alert.transactionAmount && alert.transactionCurrency && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                      Amount
                    </p>
                    <p className="mt-1 font-mono text-lg font-bold text-text-primary">
                      {alert.transactionCurrency}{' '}
                      {parseFloat(alert.transactionAmount).toLocaleString('en-US', {
                        minimumFractionDigits: 2,
                      })}
                    </p>
                  </div>
                )}

                {alert.transactionType && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                      Transaction Type
                    </p>
                    <p className="mt-1 text-lg font-semibold text-text-primary">
                      {alert.transactionType.replace(/_/g, ' ')}
                    </p>
                  </div>
                )}

                {alert.txReference && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                      Reference Number
                    </p>
                    <p className="mt-1 font-mono text-sm text-text-secondary">{alert.txReference}</p>
                  </div>
                )}

                {alert.accountNumber && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                      Account Number
                    </p>
                    <p className="mt-1 font-mono text-sm text-text-secondary">{alert.accountNumber}</p>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Device / Network Context (if applicable) */}
          {isLogin && (
            <section className="rounded-lg border border-border-primary bg-surface-secondary p-5">
              <div className="mb-4 flex items-center gap-3">
                <div className="rounded-lg bg-green-50 p-2">
                  <Smartphone className="h-5 w-5 text-green-600" />
                </div>
                <h3 className="text-lg font-semibold text-text-primary">Device / Network Context</h3>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                {alert.loginDeviceId && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                      Device ID
                    </p>
                    <p className="mt-1 font-mono text-sm text-text-secondary">{alert.loginDeviceId}</p>
                  </div>
                )}

                {alert.loginIpAddress && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                      IP Address
                    </p>
                    <p className="mt-1 font-mono text-sm text-text-secondary">{alert.loginIpAddress}</p>
                  </div>
                )}

                {alert.loginLocation && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                      Location
                    </p>
                    <div className="mt-1 flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-text-tertiary" />
                      <p className="text-sm text-text-secondary">{alert.loginLocation}</p>
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* User Information */}
          <section className="rounded-lg border border-border-primary bg-surface-secondary p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-lg bg-indigo-50 p-2">
                <Activity className="h-5 w-5 text-indigo-600" />
              </div>
              <h3 className="text-lg font-semibold text-text-primary">User Information</h3>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {alert.userName && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                    User Name
                  </p>
                  <p className="mt-1 text-sm font-semibold text-text-primary">{alert.userName}</p>
                </div>
              )}

              {alert.userPhone && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                    Phone Number
                  </p>
                  <p className="mt-1 font-mono text-sm text-text-secondary">{alert.userPhone}</p>
                </div>
              )}

              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  Alert Created
                </p>
                <div className="mt-1 flex items-center gap-2">
                  <Clock className="h-4 w-4 text-text-tertiary" />
                  <p className="text-sm text-text-secondary">
                    {new Date(alert.createdAt).toLocaleString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              </div>

              {alert.autoActionTaken && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                    Auto Action Taken
                  </p>
                  <p className="mt-1 rounded-md bg-purple-100 px-2 py-1 text-sm font-semibold text-purple-800">
                    {alert.autoActionTaken}
                  </p>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </>
  )
}
