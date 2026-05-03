import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
import { DataTable, type Column } from '../../../shared/components/ui/DataTable'
import { Input } from '../../../shared/components/ui/Input'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { getStaffTransactionDetail, getStaffTransactions, reverseStaffTransaction, type StaffTransactionDetail } from '../../staff/services/staff-service'
import type { Transaction } from '../../ledger/types'

export function StaffLedgerPage() {
  const queryClient = useQueryClient()
  const [searchInput, setSearchInput] = useState('')
  const [q, setQ] = useState('')
  const [type, setType] = useState('')
  const [currency, setCurrency] = useState('')
  const [selectedRef, setSelectedRef] = useState<string | null>(null)

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setQ(searchInput.trim())
    }, 300)
    return () => window.clearTimeout(handle)
  }, [searchInput])

  const listParams = useMemo(() => ({
    q: q.trim() || undefined,
    type: type || undefined,
    currency: currency || undefined,
    limit: 200,
  }), [q, type, currency])

  const txQuery = useQuery({
    queryKey: ['staff-transactions', listParams],
    queryFn: () => getStaffTransactions(listParams),
    placeholderData: (prev) => prev,
  })

  const detailQuery = useQuery({
    queryKey: ['staff-transaction-detail', selectedRef],
    queryFn: () => getStaffTransactionDetail(selectedRef!),
    enabled: selectedRef != null,
  })

  const reverseMutation = useMutation({
    mutationFn: (reference: string) => reverseStaffTransaction(reference, 'Staff reversal review.'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['staff-transactions'] }),
  })

  const columns: Column<Transaction>[] = [
    {
      key: 'ref',
      header: 'Reference',
      render: (tx) => (
        <div>
          <p className="font-mono text-xs text-text-primary">{tx.reference}</p>
          <p className="text-xs text-text-tertiary capitalize">{tx.type.replace(/_/g, ' ').toLowerCase()}</p>
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      render: (tx) => (
        <span className="font-bold text-text-primary">
          {tx.currency} {Number(tx.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (tx) => (
        <Badge variant={tx.status === 'COMPLETED' ? 'success' : tx.status === 'REVERSED' ? 'info' : 'warning'}>
          {tx.status}
        </Badge>
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
    {
      key: 'actions',
      header: '',
      render: (tx) => (
        <Button
          className="!min-h-0 px-3 py-1.5 text-xs"
          disabled={tx.status !== 'COMPLETED' || reverseMutation.isPending}
          title={tx.status !== 'COMPLETED' ? 'Only completed transactions can be reversed.' : undefined}
          onClick={() => reverseMutation.mutate(tx.reference)}
          variant="danger"
        >
          Reverse
        </Button>
      ),
    },
  ]

  if (txQuery.isError) {
    return (
      <StatusNoticeCard
        title="Ledger unavailable"
        message="Transactions could not be loaded. Please retry."
        variant="error"
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-text-tertiary">
          {txQuery.data?.length ?? 0} transactions
        </p>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Input
            placeholder="Search reference or phone…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="min-h-[44px] w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none transition-colors focus:border-brand-primary sm:w-56"
          >
            <option value="">All types</option>
            <option value="TRANSFER">TRANSFER</option>
            <option value="DEPOSIT">DEPOSIT</option>
            <option value="WITHDRAWAL">WITHDRAWAL</option>
            <option value="QR_PAYMENT">QR_PAYMENT</option>
            <option value="BILL_PAYMENT">BILL_PAYMENT</option>
          </select>
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="min-h-[44px] w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none transition-colors focus:border-brand-primary sm:w-44"
          >
            <option value="">All currencies</option>
            <option value="USD">USD</option>
            <option value="SOS">SOS</option>
          </select>
        </div>
      </div>

      {txQuery.isPending && !txQuery.data ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : (
        <div className="rounded-xl border border-border bg-surface-primary">
          <DataTable
            columns={columns}
            rows={txQuery.data ?? []}
            keyExtractor={(tx) => tx.id}
            emptyMessage="No transactions available."
            onRowClick={(tx) => setSelectedRef(tx.reference)}
          />
        </div>
      )}

      {selectedRef && (
        <TransactionDetailModal
          reference={selectedRef}
          data={detailQuery.data}
          loading={detailQuery.isLoading}
          error={detailQuery.isError}
          onClose={() => setSelectedRef(null)}
        />
      )}
    </div>
  )
}

function TransactionDetailModal({
  reference,
  data,
  loading,
  error,
  onClose,
}: {
  reference: string
  data?: StaffTransactionDetail
  loading: boolean
  error: boolean
  onClose: () => void
}) {
  const debits = (data?.entries ?? []).filter((e) => e.entryType === 'DEBIT')
  const credits = (data?.entries ?? []).filter((e) => e.entryType === 'CREDIT')
  const fromParty = debits[0]
  const toParty = credits[0]

  const originLabel =
    data?.tellerOperation
      ? `Teller ${String(data.tellerOperation).toUpperCase()}`
      : data?.channel
        ? `Channel: ${data.channel}`
        : 'Origin unknown'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div className="relative w-full max-w-2xl rounded-2xl bg-surface-primary p-6 shadow-md">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs text-text-tertiary">Transaction</p>
            <p className="font-mono text-sm font-semibold text-text-primary">{reference}</p>
            {data && (
              <p className="mt-1 text-xs text-text-tertiary">
                {data.type} · {data.status} · {new Date(data.occurredAt).toLocaleString()} · {originLabel}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-3 py-2 text-sm font-semibold text-text-secondary hover:bg-surface-secondary transition-colors"
          >
            Close
          </button>
        </div>

        <div className="mt-4">
          {loading ? (
            <p className="text-sm text-text-secondary">Loading details…</p>
          ) : error || !data ? (
            <StatusNoticeCard title="Detail unavailable" message="Unable to load transaction details." variant="warning" />
          ) : (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-border p-4">
                  <p className="text-xs font-semibold text-text-secondary">From</p>
                  <p className="mt-1 text-sm font-semibold text-text-primary">{fromParty?.ownerName ?? '—'}</p>
                  <p className="text-xs text-text-tertiary">{fromParty?.ownerPhone ?? '—'}</p>
                  <p className="mt-2 font-mono text-xs text-text-secondary">{fromParty?.accountNumber ?? '—'}</p>
                </div>
                <div className="rounded-xl border border-border p-4">
                  <p className="text-xs font-semibold text-text-secondary">To</p>
                  <p className="mt-1 text-sm font-semibold text-text-primary">{toParty?.ownerName ?? '—'}</p>
                  <p className="text-xs text-text-tertiary">{toParty?.ownerPhone ?? '—'}</p>
                  <p className="mt-2 font-mono text-xs text-text-secondary">{toParty?.accountNumber ?? '—'}</p>
                </div>
              </div>

              <div className="rounded-xl border border-border p-4">
                <p className="text-xs font-semibold text-text-secondary">Entries</p>
                <div className="mt-2 space-y-2">
                  {data.entries.map((e) => (
                    <div key={e.id} className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2">
                      <div>
                        <p className="text-xs font-semibold text-text-primary">{e.entryType}</p>
                        <p className="text-[11px] text-text-tertiary">
                          {e.ownerName ?? '—'} · {e.ownerPhone ?? '—'}
                        </p>
                        <p className="font-mono text-[11px] text-text-tertiary">{e.accountNumber}</p>
                      </div>
                      <p className="text-xs font-semibold text-text-primary">
                        {data.currency} {Number(e.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
