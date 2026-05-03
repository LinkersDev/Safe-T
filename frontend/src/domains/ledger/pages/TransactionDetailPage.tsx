import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Badge } from '../../../shared/components/ui/Badge'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { getTransactionDetail } from '../services/ledger-service'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { cn } from '../../../core/utils/cn'

const STATUS_VARIANT: Record<string, 'success' | 'danger' | 'warning' | 'info'> = {
  COMPLETED: 'success',
  FAILED: 'danger',
  PENDING: 'warning',
  REVERSED: 'info',
}

const TX_TYPE_LABELS: Record<string, string> = {
  TRANSFER: 'Transfer',
  DEPOSIT: 'Deposit',
  WITHDRAWAL: 'Withdrawal',
  QR_PAYMENT: 'QR Pay',
  BILL_PAYMENT: 'Bill Pay',
  FEE: 'Fee',
}

const TX_TYPE_ICONS: Record<string, string> = {
  TRANSFER: '→',
  DEPOSIT: '⬇',
  WITHDRAWAL: '⬆',
  QR_PAYMENT: '▣',
  BILL_PAYMENT: '⚡',
  FEE: '💸',
}

export function TransactionDetailPage() {
  const { reference } = useParams<{ reference: string }>()
  const navigate = useNavigate()

  const { data: tx, isLoading, isError } = useQuery({
    queryKey: ['transaction-detail', reference],
    queryFn: () => getTransactionDetail(reference!),
    enabled: Boolean(reference),
  })

  if (isLoading) {
    return (
      <div className="mx-auto max-w-lg space-y-4">
        <Skeleton className="h-8 w-40 rounded-lg" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    )
  }

  if (isError || !tx) {
    return (
      <div className="mx-auto max-w-lg text-center py-16">
        <p className="text-text-secondary">Transaction not found.</p>
        <button
          onClick={() => navigate(ROUTE_PATHS.ledger)}
          className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
        >
          Back to history
        </button>
      </div>
    )
  }

  const isCredit = tx.type === 'DEPOSIT'

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <button
        onClick={() => navigate(ROUTE_PATHS.ledger)}
        className="flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
      >
        ← Back to transaction history
      </button>

      {/* Receipt card */}
      <div className="overflow-hidden rounded-2xl border border-border bg-surface-primary shadow-sm">
        {/* Header strip */}
        <div
          className={cn(
            'flex flex-col items-center gap-2 px-6 py-8',
            isCredit ? 'bg-emerald-50' : 'bg-indigo-50',
          )}
        >
          <div
            className={cn(
              'flex h-14 w-14 items-center justify-center rounded-full text-2xl',
              isCredit ? 'bg-emerald-100 text-emerald-700' : 'bg-indigo-100 text-indigo-700',
            )}
          >
            {TX_TYPE_ICONS[tx.type] ?? '💳'}
          </div>
          <p className="text-sm font-medium text-text-secondary">
            {TX_TYPE_LABELS[tx.type] ?? tx.type}
          </p>
          <p
            className={cn(
              'text-3xl font-bold',
              isCredit ? 'text-emerald-700' : 'text-text-primary',
            )}
          >
            {isCredit ? '+' : '-'}
            {tx.currency}&nbsp;
            {Number(tx.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </p>
          <Badge variant={STATUS_VARIANT[tx.status] ?? 'info'}>{tx.status}</Badge>
        </div>

        {/* Detail rows */}
        <div className="divide-y divide-border px-6">
          <DetailRow label="Reference" value={tx.reference} mono />
          {tx.counterpartyDisplay ? (
            <DetailRow label="Counterparty" value={tx.counterpartyDisplay} />
          ) : null}
          <DetailRow label="Description" value={tx.description} />
          <DetailRow
            label="Date & Time"
            value={new Date(tx.createdAt).toLocaleString('en-US', {
              dateStyle: 'long',
              timeStyle: 'short',
            })}
          />
          <DetailRow label="Currency" value={tx.currency} />
          <DetailRow label="Status" value={tx.status} />
        </div>
      </div>
    </div>
  )
}

function DetailRow({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3">
      <span className="text-sm text-text-secondary shrink-0">{label}</span>
      <span
        className={cn(
          'text-sm font-medium text-text-primary text-right break-all',
          mono && 'font-mono',
        )}
      >
        {value}
      </span>
    </div>
  )
}
