import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { Card } from '../../../shared/components/ui/Card'
import { Badge } from '../../../shared/components/ui/Badge'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { getAccounts } from '../services/account-service'
import { getLedger } from '../../ledger/services/ledger-service'
import { useAuthSession } from '../../security/hooks/useAuthSession'

const QUICK_ACTIONS = [
  { label: 'Send Money',  icon: '→', path: ROUTE_PATHS.transfer,   color: 'bg-indigo-500' },
  { label: 'QR Pay',     icon: '▣', path: ROUTE_PATHS.qrPayment,  color: 'bg-violet-500' },
  { label: 'Pay Bills',  icon: '⚡', path: ROUTE_PATHS.billPayment, color: 'bg-amber-500' },
  { label: 'History',   icon: '↕', path: ROUTE_PATHS.ledger,      color: 'bg-slate-500'  },
]

export function DashboardPage() {
  const { user } = useAuthSession()
  const [showAccountNumber, setShowAccountNumber] = useState(false)
  const { data: accounts, isLoading: accountsLoading } = useQuery({ queryKey: ['accounts'], queryFn: getAccounts })
  const { data: transactions, isLoading: txLoading } = useQuery({ queryKey: ['ledger', 5], queryFn: () => getLedger({ limit: 5 }) })

  const primaryAccount = accounts?.[0]

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h2 className="text-xl font-bold text-text-primary">
          Good day, {user?.fullName?.split(' ')[0]} 👋
        </h2>
        <p className="mt-0.5 text-sm text-text-tertiary">Here's your financial overview</p>
      </div>

      {/* Account balance card */}
      {accountsLoading ? (
        <Skeleton className="h-36 w-full rounded-2xl" />
      ) : primaryAccount ? (
        <div className="rounded-2xl bg-gradient-to-br from-indigo-600 to-indigo-800 p-6 text-white shadow-lg">
          <p className="text-sm font-medium text-indigo-200">Available Balance</p>
          <p className="mt-2 text-4xl font-bold tracking-tight">
            {primaryAccount.currency} {primaryAccount.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </p>
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <p className="text-sm text-indigo-200">
                {showAccountNumber ? primaryAccount.accountNumber : `•••• •••• ${primaryAccount.accountNumber.slice(-4)}`}
              </p>
              <button
                type="button"
                onClick={() => setShowAccountNumber((v) => !v)}
                className="rounded-md p-1 text-indigo-200 hover:text-white transition-colors"
                aria-label={showAccountNumber ? 'Hide account number' : 'Show account number'}
              >
                👁
              </button>
            </div>
            <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${primaryAccount.status === 'ACTIVE' ? 'bg-emerald-500' : 'bg-rose-500'}`}>
              {primaryAccount.status}
            </span>
          </div>
        </div>
      ) : (
        <Card className="text-center py-8 text-text-tertiary text-sm">No accounts found.</Card>
      )}

      {/* Other accounts */}
      {!accountsLoading && accounts && accounts.length > 1 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {accounts.slice(1).map((acc) => (
            <Card key={acc.id} className="flex items-center justify-between">
              <div>
                <p className="text-xs text-text-tertiary">{acc.label}</p>
                <p className="text-lg font-bold text-text-primary mt-0.5">
                  {acc.currency} {acc.balance.toLocaleString()}
                </p>
              </div>
              <Badge variant={acc.status === 'ACTIVE' ? 'success' : 'danger'}>{acc.status}</Badge>
            </Card>
          ))}
        </div>
      )}

      {/* Quick actions */}
      <div>
        <p className="mb-3 text-sm font-semibold text-text-secondary">Quick Actions</p>
        <div className="grid grid-cols-4 gap-3">
          {QUICK_ACTIONS.map(({ label, icon, path, color }) => (
            <Link
              key={path}
              to={path}
              className="flex flex-col items-center gap-2 rounded-xl border border-border bg-surface-primary p-3 text-center shadow-sm hover:shadow-md transition-shadow"
            >
              <div className={`flex h-10 w-10 items-center justify-center rounded-xl text-white text-lg ${color}`}>
                {icon}
              </div>
              <span className="text-xs font-medium text-text-secondary leading-tight">{label}</span>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent transactions */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-semibold text-text-secondary">Recent Transactions</p>
          <Link to={ROUTE_PATHS.ledger} className="text-xs font-semibold text-indigo-600 hover:underline">
            View all
          </Link>
        </div>
        {txLoading ? (
          <div className="space-y-2">
            {[1,2,3].map(i => <Skeleton key={i} className="h-14 w-full rounded-xl" />)}
          </div>
        ) : transactions?.length ? (
          <Card className="divide-y divide-border p-0 overflow-hidden">
            {transactions.map((tx) => {
              const isCredit = tx.type === 'DEPOSIT'
              return (
                <div key={tx.id} className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className={`flex h-8 w-8 items-center justify-center rounded-full text-sm ${isCredit ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'}`}>
                      {isCredit ? '↓' : '↑'}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-text-primary truncate max-w-40">{tx.description}</p>
                      <p className="text-xs text-text-tertiary">{new Date(tx.createdAt).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <span className={`text-sm font-bold ${isCredit ? 'text-emerald-600' : 'text-text-primary'}`}>
                    {isCredit ? '+' : '-'}{tx.currency} {tx.amount.toLocaleString()}
                  </span>
                </div>
              )
            })}
          </Card>
        ) : (
          <Card className="py-8 text-center text-sm text-text-tertiary">No recent transactions.</Card>
        )}
      </div>
    </div>
  )
}
