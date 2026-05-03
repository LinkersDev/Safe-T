import { useState, type FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Card } from '../../../shared/components/ui/Card'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { DataTable, type Column } from '../../../shared/components/ui/DataTable'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import { getStaffAccount } from '../../staff-accounts/services/staff-account-service'
import { getAccountTransactions, type TellerTx } from '../services/teller-service'

export function TellerAccountTransactionsPage() {
  const toast = useToast()
  const [lookupValue, setLookupValue] = useState('')
  const [accountId, setAccountId] = useState<string | null>(null)

  const lookupMutation = useMutation({
    mutationFn: getStaffAccount,
    onSuccess: (acc) => setAccountId(acc.id),
    onError: () => toast.error('Account not found.'),
  })

  function handleLookup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAccountId(null)
    lookupMutation.mutate(lookupValue)
  }

  const txQuery = useQuery({
    queryKey: ['teller-account-transactions', accountId],
    queryFn: () => getAccountTransactions(accountId as string),
    enabled: Boolean(accountId),
  })

  const columns: Column<TellerTx>[] = [
    {
      key: 'ref',
      header: 'Reference',
      render: (tx) => (
        <div>
          <p className="font-mono text-xs text-text-primary">{tx.reference_number}</p>
          <p className="text-xs text-text-tertiary capitalize">{tx.transaction_type.replace(/_/g, ' ').toLowerCase()}</p>
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      render: (tx) => (
        <span className="font-bold text-text-primary">
          {tx.currency_code} {Number(tx.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (tx) => <span className="text-xs text-text-secondary">{tx.status}</span>,
    },
    {
      key: 'date',
      header: 'Date',
      render: (tx) => (
        <span className="text-xs text-text-tertiary whitespace-nowrap">
          {new Date(tx.occurred_at).toLocaleDateString()}
        </span>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <Card as="form" className="max-w-lg space-y-3" onSubmit={handleLookup}>
        <Input
          inputMode="tel"
          placeholder="Phone (+E.164), account number, or account id"
          value={lookupValue}
          onChange={(e) => setLookupValue(e.target.value)}
          required
        />
        <Button loading={lookupMutation.isPending} type="submit">
          Lookup
        </Button>
      </Card>

      {txQuery.isLoading && accountId ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : txQuery.isError ? (
        <StatusNoticeCard title="Transactions unavailable" message="Could not load account transactions." variant="error" />
      ) : (
        accountId && (
          <DataTable
            columns={columns}
            rows={txQuery.data ?? []}
            keyExtractor={(t) => String(t.id)}
            emptyMessage="No transactions available."
          />
        )
      )}
    </div>
  )
}

