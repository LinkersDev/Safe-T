import { X, AlertTriangle, ArrowRightLeft, ArrowDownLeft, ArrowUpRight, Smartphone, CreditCard, MapPin, Clock, Shield, User } from 'lucide-react'
import type { FraudAlert } from '../../staff/types'

type AlertDetailDrawerProps = {
  alert: FraudAlert | null
  isOpen: boolean
  onClose: () => void
}

/* ------------------------------------------------------------------ */
// Helpers
/* ------------------------------------------------------------------ */

function getSeverityColor(sev: string) {
  switch (sev) {
    case 'CRITICAL': return 'bg-red-600 text-white'
    case 'HIGH':     return 'bg-orange-500 text-white'
    case 'MEDIUM':   return 'bg-amber-500 text-white'
    default:        return 'bg-blue-500 text-white'
  }
}

function getScoreBarColor(score: number) {
  if (score >= 75) return 'bg-red-500'
  if (score >= 50) return 'bg-orange-500'
  if (score >= 25) return 'bg-amber-500'
  return 'bg-green-500'
}

function getScoreLabel(score: number) {
  if (score >= 75) return 'CRITICAL'
  if (score >= 50) return 'HIGH'
  if (score >= 25) return 'MEDIUM'
  return 'LOW'
}

function getAlertIcon(alert: FraudAlert) {
  const type = alert.alertType?.toUpperCase() || ''
  const tx   = alert.transactionType?.toUpperCase() || ''
  if (type.includes('LOGIN')) return <Smartphone className="h-6 w-6" />
  if (tx.includes('TRANSFER')) return <ArrowRightLeft className="h-6 w-6" />
  if (tx.includes('WITHDRAW')) return <ArrowDownLeft className="h-6 w-6" />
  if (tx.includes('DEPOSIT'))  return <ArrowUpRight className="h-6 w-6" />
  return <AlertTriangle className="h-6 w-6" />
}

function getAlertLabel(alert: FraudAlert) {
  const type = alert.alertType?.toUpperCase() || ''
  const tx   = alert.transactionType?.toUpperCase() || ''
  if (type.includes('LOGIN')) return 'Login'
  if (tx.includes('TRANSFER')) return 'Transfer'
  if (tx.includes('WITHDRAW')) return 'Withdrawal'
  if (tx.includes('DEPOSIT'))  return 'Deposit'
  if (tx.includes('QR'))       return 'QR Payment'
  if (tx.includes('BILL'))     return 'Bill Payment'
  return 'Transaction'
}

/* ------------------------------------------------------------------ */
// Component
/* ------------------------------------------------------------------ */

export function AlertDetailDrawer({ alert, isOpen, onClose }: AlertDetailDrawerProps) {
  if (!isOpen || !alert) return null

  const score       = (alert.combinedScore != null && alert.combinedScore > 0)
    ? alert.combinedScore
    : (parseFloat(alert.riskScore) || 0)
  const ruleScore   = alert.ruleBasedScore ?? 0
  const mlProb      = alert.mlFraudProbability
  const hasML       = mlProb !== null && mlProb !== undefined
  const mlScore     = hasML ? Math.round(mlProb * 100) : 0
  const sevLabel    = alert.severity
  const sevColor    = getSeverityColor(sevLabel)
  const barColor    = getScoreBarColor(score)
  const scoreLabel  = getScoreLabel(score)

  const isTransaction = alert.alertType?.toUpperCase().includes('TRANSACTION')
  const isLogin       = alert.alertType?.toUpperCase().includes('LOGIN')

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl overflow-y-auto bg-white shadow-2xl">

        {/* ========== HEADER ========== */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-4">
          <div className="flex items-center gap-3">
            <div className={`rounded-lg p-2 ${sevColor}`}>
              {getAlertIcon(alert)}
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                Alert #{alert.id} &mdash; {getAlertLabel(alert)}
              </h2>
              <p className="text-xs text-gray-500">
                {new Date(alert.createdAt).toLocaleString('en-GB', {
                  day: 'numeric', month: 'short', year: 'numeric',
                  hour: '2-digit', minute: '2-digit',
                })}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-700">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-5 p-5">

          {/* ========== SEVERITY & SCORE BANNER ========== */}
          <div className="rounded-xl border-2 border-gray-100 bg-gray-50 p-5">
            <div className="flex items-center justify-between">
              <div>
                <span className={`inline-block rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide ${sevColor}`}>
                  {sevLabel} PRIORITY
                </span>
                {alert.status === 'OPEN' && (
                  <span className="ml-2 inline-block rounded-full bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-700">
                    OPEN
                  </span>
                )}
                {alert.autoActionTaken && (
                  <span className="ml-2 inline-block rounded-full bg-purple-100 px-2 py-1 text-xs font-semibold text-purple-700">
                    AUTO-ACTIONED
                  </span>
                )}
              </div>
              <div className="text-right">
                <p className="text-4xl font-black text-gray-900">{score}</p>
                <p className={`text-sm font-bold ${scoreLabel === 'CRITICAL' ? 'text-red-600' : scoreLabel === 'HIGH' ? 'text-orange-600' : scoreLabel === 'MEDIUM' ? 'text-amber-600' : 'text-green-600'}`}>
                  {scoreLabel}
                </p>
              </div>
            </div>

            {/* Score bar */}
            <div className="mt-4">
              <div className="h-3 overflow-hidden rounded-full bg-gray-200">
                <div className={`h-full ${barColor}`} style={{ width: `${Math.min(score, 100)}%` }} />
              </div>
              <div className="mt-1 flex justify-between text-[10px] font-medium text-gray-400 uppercase">
                <span>Safe</span>
                <span>Low</span>
                <span>Medium</span>
                <span>High</span>
                <span>Critical</span>
              </div>
            </div>

            {/* Score breakdown row */}
            <div className="mt-4 grid grid-cols-3 gap-3 text-center">
              <div className="rounded-lg bg-white p-2">
                <p className="text-[10px] font-bold uppercase text-gray-400">Rule Score</p>
                <p className="text-lg font-bold text-gray-800">{ruleScore}</p>
              </div>
              <div className="rounded-lg bg-white p-2">
                <p className="text-[10px] font-bold uppercase text-gray-400">ML Score</p>
                <p className="text-lg font-bold text-gray-800">{hasML ? `${mlScore}%` : '—'}</p>
              </div>
              <div className="rounded-lg bg-white p-2">
                <p className="text-[10px] font-bold uppercase text-gray-400">Combined</p>
                <p className="text-lg font-bold text-gray-800">{score}</p>
              </div>
            </div>
          </div>

          {/* ========== WHY IT TRIGGERED ========== */}
          {alert.rulesTriggered && alert.rulesTriggered.length > 0 && (
            <div className="rounded-xl border border-red-100 bg-red-50 p-4">
              <div className="flex items-center gap-2 text-red-700">
                <Shield className="h-4 w-4" />
                <p className="text-xs font-bold uppercase tracking-wide">Why This Alert Fired</p>
              </div>
              <ul className="mt-2 space-y-1.5">
                {alert.rulesTriggered.map((rule, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-red-800">
                    <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-red-500" />
                    {rule}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* ========== EVENT DETAILS ========== */}
          {isTransaction && (
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
              <div className="flex items-center gap-2 text-blue-700">
                <CreditCard className="h-4 w-4" />
                <p className="text-xs font-bold uppercase tracking-wide">Transaction Details</p>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3">
                {alert.transactionAmount && alert.transactionCurrency && (
                  <div>
                    <p className="text-[10px] font-bold uppercase text-blue-400">Amount</p>
                    <p className="font-mono text-lg font-bold text-blue-900">
                      {alert.transactionCurrency} {parseFloat(alert.transactionAmount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </p>
                  </div>
                )}
                {alert.transactionType && (
                  <div>
                    <p className="text-[10px] font-bold uppercase text-blue-400">Type</p>
                    <p className="text-sm font-semibold text-blue-900">{alert.transactionType.replace(/_/g, ' ')}</p>
                  </div>
                )}
                {alert.txReference && (
                  <div className="col-span-2">
                    <p className="text-[10px] font-bold uppercase text-blue-400">Reference</p>
                    <p className="font-mono text-sm text-blue-800">{alert.txReference}</p>
                  </div>
                )}
                {alert.accountNumber && (
                  <div>
                    <p className="text-[10px] font-bold uppercase text-blue-400">Account</p>
                    <p className="font-mono text-sm text-blue-800">{alert.accountNumber}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {isLogin && (
            <div className="rounded-xl border border-green-100 bg-green-50 p-4">
              <div className="flex items-center gap-2 text-green-700">
                <Smartphone className="h-4 w-4" />
                <p className="text-xs font-bold uppercase tracking-wide">Login Details</p>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3">
                {alert.loginDeviceId && (
                  <div className="col-span-2">
                    <p className="text-[10px] font-bold uppercase text-green-400">Device ID</p>
                    <p className="font-mono text-sm text-green-900">{alert.loginDeviceId}</p>
                  </div>
                )}
                {alert.loginIpAddress && (
                  <div>
                    <p className="text-[10px] font-bold uppercase text-green-400">IP Address</p>
                    <p className="font-mono text-sm text-green-900">{alert.loginIpAddress}</p>
                  </div>
                )}
                {alert.loginLocation && (
                  <div>
                    <p className="text-[10px] font-bold uppercase text-green-400">Location</p>
                    <div className="flex items-center gap-1 text-sm text-green-900">
                      <MapPin className="h-3.5 w-3.5" /> {alert.loginLocation}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ========== WHO ========== */}
          <div className="rounded-xl border border-gray-100 bg-white p-4">
            <div className="flex items-center gap-2 text-gray-500">
              <User className="h-4 w-4" />
              <p className="text-xs font-bold uppercase tracking-wide">Who</p>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3">
              {alert.userName && (
                <div>
                  <p className="text-[10px] font-bold uppercase text-gray-400">Name</p>
                  <p className="text-sm font-semibold text-gray-900">{alert.userName}</p>
                </div>
              )}
              {alert.userPhone && (
                <div>
                  <p className="text-[10px] font-bold uppercase text-gray-400">Phone</p>
                  <p className="font-mono text-sm text-gray-700">{alert.userPhone}</p>
                </div>
              )}
              <div>
                <p className="text-[10px] font-bold uppercase text-gray-400">Alert Created</p>
                <div className="flex items-center gap-1 text-sm text-gray-700">
                  <Clock className="h-3.5 w-3.5" />
                  {new Date(alert.createdAt).toLocaleString('en-GB', {
                    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                  })}
                </div>
              </div>
              {alert.autoActionTaken && (
                <div>
                  <p className="text-[10px] font-bold uppercase text-gray-400">Auto Action</p>
                  <span className="inline-block rounded bg-purple-100 px-2 py-0.5 text-xs font-semibold text-purple-700">
                    {alert.autoActionTaken}
                  </span>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </>
  )
}
