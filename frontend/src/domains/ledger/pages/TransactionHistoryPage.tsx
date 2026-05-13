import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Badge } from '../../../shared/components/ui/Badge'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { DataTable, type Column } from '../../../shared/components/ui/DataTable'
import { getLedger } from '../services/ledger-service'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import type { Transaction } from '../types'
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

export function TransactionHistoryPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['ledger', statusFilter, typeFilter],
    queryFn: () => getLedger({ status: statusFilter || undefined, type: typeFilter || undefined }),
  })

  const columns: Column<Transaction>[] = [
    {
      key: 'type',
      header: 'Type',
      render: (tx) => (
        <span className="rounded-md bg-surface-secondary px-2 py-0.5 text-xs font-medium text-text-secondary">
          {TX_TYPE_LABELS[tx.type] ?? tx.type}
        </span>
      ),
    },
    {
      key: 'counterparty',
      header: 'Counterparty',
      render: (tx) => (
        <span className="text-sm text-text-primary">{tx.counterpartyDisplay ?? '—'}</span>
      ),
    },
    {
      key: 'description',
      header: 'Description',
      render: (tx) => (
        <div>
          <p className="font-medium text-text-primary text-sm truncate max-w-48">{tx.description}</p>
          <p className="text-xs text-text-tertiary">{tx.reference}</p>
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      render: (tx) => {
        const isIncoming = tx.direction === 'incoming'
        return (
          <span className={cn('font-bold text-sm', isIncoming ? 'text-emerald-600' : 'text-text-primary')}>
            {isIncoming ? '+' : '-'}{tx.currency} {Number(tx.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </span>
        )
      },
    },
    {
      key: 'status',
      header: 'Status',
      render: (tx) => (
        <Badge variant={STATUS_VARIANT[tx.status] ?? 'info'}>{tx.status}</Badge>
      ),
    },
    {
      key: 'date',
      header: 'Date',
      render: (tx) => (
        <span className="text-xs text-text-tertiary whitespace-nowrap">
          {new Date(tx.createdAt).toLocaleString()}
        </span>
      ),
    },
  ]

  return (
    <div className="space-y-5">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none focus:border-indigo-500"
        >
          <option value="">All statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="PENDING">Pending</option>
          <option value="FAILED">Failed</option>
          <option value="REVERSED">Reversed</option>
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-lg border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none focus:border-indigo-500"
        >
          <option value="">All types</option>
          <option value="TRANSFER">Transfer</option>
          <option value="DEPOSIT">Deposit</option>
          <option value="QR_PAYMENT">QR Pay</option>
          <option value="BILL_PAYMENT">Bill Pay</option>
          <option value="WITHDRAWAL">Withdrawal</option>
        </select>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-14 w-full rounded-xl" />)}
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={data ?? []}
          keyExtractor={(tx) => tx.id}
          emptyMessage="No transactions found for the selected filters."
          onRowClick={(tx) => navigate(ROUTE_PATHS.transactionDetail(tx.reference))}
        />
      )}
    </div>
  )
}
