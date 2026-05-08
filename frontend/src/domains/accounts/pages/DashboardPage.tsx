import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Send, QrCode, Receipt, History, Eye, EyeOff, ArrowDownLeft, ArrowUpRight } from 'lucide-react'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { Card } from '../../../shared/components/ui/Card'
import { Badge } from '../../../shared/components/ui/Badge'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { getAccounts } from '../services/account-service'
import { getLedger } from '../../ledger/services/ledger-service'
import { useAuthSession } from '../../security/hooks/useAuthSession'

const QUICK_ACTIONS = [
  { label: 'Send Money', icon: Send, path: ROUTE_PATHS.transfer,   accent: 'blue' },
  { label: 'QR Pay',     icon: QrCode, path: ROUTE_PATHS.qrPayment,  accent: 'green' },
  { label: 'Pay Bills',  icon: Receipt, path: ROUTE_PATHS.billPayment, accent: 'amber' },
  { label: 'History',    icon: History, path: ROUTE_PATHS.ledger,      accent: 'slate' },
]

const accentClasses: Record<string, string> = {
  blue:   'border-l-blue-500',
  green:  'border-l-emerald-500',
  amber:  'border-l-amber-500',
  slate:  'border-l-slate-400',
}

const iconColors: Record<string, string> = {
  blue:   'bg-blue-50 text-blue-600',
  green:  'bg-emerald-50 text-emerald-600',
  amber:  'bg-amber-50 text-amber-600',
  slate:  'bg-slate-50 text-slate-600',
}

export function DashboardPage() {
  const { user } = useAuthSession()
  const [showAccountNumber, setShowAccountNumber] = useState(false)
  const { data: accounts, isLoading: accountsLoading } = useQuery({ queryKey: ['accounts'], queryFn: getAccounts })
  const { data: transactions, isLoading: txLoading } = useQuery({ queryKey: ['ledger', 5], queryFn: () => getLedger({ limit: 5 }) })

  const primaryAccount = accounts?.[0]

  return (
    <div className="space-y-8">
      {/* Welcome */}
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-slate-900">
          Good day, {user?.fullName?.split(' ')[0]}
        </h2>
        <p className="text-sm text-slate-500 leading-relaxed">Here's your financial overview</p>
      </div>

      {/* Account balance card */}
      {accountsLoading ? (
        <Skeleton className="h-36 w-full rounded-2xl" />
      ) : primaryAccount ? (
        <div 
          className="rounded-2xl p-6 text-white relative overflow-hidden"
          style={{ backgroundColor: '#0A2540', boxShadow: '0 4px 20px rgba(10, 37, 64, 0.15)' }}
        >
          <p className="text-sm font-medium text-slate-400">Available Balance</p>
          <p className="mt-2 text-4xl font-bold tracking-tight">
            {primaryAccount.currency} {primaryAccount.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </p>
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <p className="text-sm text-slate-400">
                {showAccountNumber ? primaryAccount.accountNumber : `•••• •••• ${primaryAccount.accountNumber.slice(-4)}`}
              </p>
              <button
                type="button"
                onClick={() => setShowAccountNumber((v) => !v)}
                className="rounded-md p-1 text-slate-400 hover:text-white transition-all"
                style={{ transition: 'all 0.2s ease' }}
                aria-label={showAccountNumber ? 'Hide account number' : 'Show account number'}
              >
                {showAccountNumber ? <EyeOff size={16} strokeWidth={2} /> : <Eye size={16} strokeWidth={2} />}
              </button>
            </div>
            <span 
              className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
              style={{ 
                backgroundColor: primaryAccount.status === 'ACTIVE' ? '#10B981' : '#F43F5E',
              }}
            >
              {primaryAccount.status}
            </span>
          </div>
        </div>
      ) : (
        <Card className="text-center py-8 text-slate-500 text-sm">No accounts found.</Card>
      )}

      {/* Other accounts */}
      {!accountsLoading && accounts && accounts.length > 1 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {accounts.slice(1).map((acc) => (
            <div
              key={acc.id}
              className="card-hover rounded-xl border border-[#E2E8F0] bg-white p-4 relative overflow-hidden border-l-[3px] border-l-slate-400"
              style={{ 
                boxShadow: '0 4px 20px rgba(10, 37, 64, 0.08)',
                transition: 'all 0.2s ease',
              }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-500">{acc.label}</p>
                  <p className="text-lg font-bold text-slate-900 mt-0.5">
                    {acc.currency} {acc.balance.toLocaleString()}
                  </p>
                </div>
                <Badge variant={acc.status === 'ACTIVE' ? 'success' : 'danger'}>{acc.status}</Badge>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Quick actions */}
      <div className="space-y-4">
        <p className="text-sm font-semibold text-slate-900">Quick Actions</p>
        <div className="grid grid-cols-4 gap-4">
          {QUICK_ACTIONS.map(({ label, icon: Icon, path, accent }) => (
            <Link
              key={path}
              to={path}
              className={`
                card-hover flex flex-col items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white p-3 text-center relative overflow-hidden
                ${accentClasses[accent]}
              `}
              style={{ 
                boxShadow: '0 4px 20px rgba(10, 37, 64, 0.08)',
                borderLeftWidth: '3px',
                transition: 'all 0.2s ease',
              }}
            >
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${iconColors[accent]}`}>
                <Icon size={20} strokeWidth={2} />
              </div>
              <span className="text-xs font-medium text-slate-700 leading-tight">{label}</span>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent transactions */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-slate-900">Recent Transactions</p>
          <Link to={ROUTE_PATHS.ledger} className="text-xs font-semibold text-blue-600 hover:underline">
            View all
          </Link>
        </div>
        {txLoading ? (
          <div className="space-y-3">
            {[1,2,3].map(i => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
          </div>
        ) : transactions?.length ? (
          <div className="space-y-3">
            {transactions.map((tx) => {
              const isCredit = tx.type === 'DEPOSIT'
              return (
                <div
                  key={tx.id}
                  className={`
                    card-hover flex items-center justify-between rounded-xl border border-[#E2E8F0] bg-white p-4 relative overflow-hidden
                    ${isCredit ? 'border-l-emerald-500' : 'border-l-rose-500'}
                  `}
                  style={{ 
                    boxShadow: '0 4px 20px rgba(10, 37, 64, 0.08)',
                    borderLeftWidth: '3px',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${isCredit ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
                      {isCredit ? <ArrowDownLeft size={18} strokeWidth={2} /> : <ArrowUpRight size={18} strokeWidth={2} />}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-900 truncate max-w-40">{tx.description}</p>
                      <p className="text-xs text-slate-500">{new Date(tx.createdAt).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <span className={`text-sm font-bold ${isCredit ? 'text-emerald-600' : 'text-slate-900'}`}>
                    {isCredit ? '+' : '-'}{tx.currency} {tx.amount.toLocaleString()}
                  </span>
                </div>
              )
            })}
          </div>
        ) : (
          <Card className="py-8 text-center text-sm text-slate-500">No recent transactions.</Card>
        )}
      </div>
    </div>
  )
}
