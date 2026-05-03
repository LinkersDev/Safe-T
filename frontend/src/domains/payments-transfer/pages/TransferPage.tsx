import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import { Input } from '../../../shared/components/ui/Input'
import { PaymentResultCard } from '../../../shared/components/financial/PaymentResultCard'
import { createIdempotencyKey } from '../../../core/api/idempotency'
import { normalizeApiError } from '../../../core/api/error-normalizer'
import { getReconciliationMessage, shouldReconcilePayment } from '../../../core/api/reconciliation'
import { getAccounts } from '../../accounts/services/account-service'
import { executeTransfer, lookupTransferRecipient } from '../services/transfer-service'
import type { TransferResult, TransferRoutePrefill } from '../types'

export function TransferPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [sourceAccountNumber, setSourceAccountNumber] = useState('')
  const [destinationPhoneNumber, setDestinationPhoneNumber] = useState('')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [pin, setPin] = useState('')
  const [idempotencyKey, setIdempotencyKey] = useState(createIdempotencyKey)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TransferResult | null>(null)
  const [qrVerify, setQrVerify] = useState<{
    phone: string
    accountNumber: string
    name: string
  } | null>(null)

  useEffect(() => {
    const s = location.state as TransferRoutePrefill | null | undefined
    if (!s?.fromQrScan || !s.destinationPhoneNumber) return

    setDestinationPhoneNumber(s.destinationPhoneNumber)
    setQrVerify({
      phone: s.destinationPhoneNumber,
      accountNumber: s.destinationAccountNumber ?? '',
      name: s.recipientFullName ?? '',
    })
    navigate(location.pathname, { replace: true, state: {} })
  }, [location.state, location.pathname, navigate])

  const accountsQuery = useQuery({
    queryKey: ['accounts'],
    queryFn: getAccounts,
  })

  const normalizedPhone = useMemo(
    () => destinationPhoneNumber.trim(),
    [destinationPhoneNumber],
  )

  const recipientQuery = useQuery({
    queryKey: ['transfer-recipient', normalizedPhone],
    queryFn: () => lookupTransferRecipient(normalizedPhone),
    enabled: normalizedPhone.length >= 7 && normalizedPhone.startsWith('+'),
    retry: false,
  })

  const recipientName = recipientQuery.data?.full_name ?? null
  const recipientNotFound = recipientQuery.isError

  const executeMutation = useMutation({
    mutationFn: executeTransfer,
    onSuccess: (transaction) => {
      setError(null)
      setResult(transaction)
    },
    onError: (nextError) => setError(normalizeApiError(nextError).detail),
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    if (recipientNotFound) {
      setError('Customer not found.')
      return
    }
    executeMutation.mutate({
      sourceAccountNumber,
      destinationPhoneNumber,
      amount,
      currencyCode: 'USD',
      description,
      pin,
      idempotencyKey,
    })
  }

  function resetTransfer() {
    setDestinationPhoneNumber('')
    setAmount('')
    setDescription('')
    setPin('')
    setIdempotencyKey(createIdempotencyKey())
    setResult(null)
    setError(null)
    setQrVerify(null)
  }

  return (
    <div className="max-w-xl">
      {result ? (
        <div className="space-y-4">
          <PaymentResultCard transaction={result} />
          <Button className="w-full" onClick={resetTransfer}>
            New transfer
          </Button>
        </div>
      ) : (
      <Card as="form" className="space-y-4" onSubmit={handleSubmit}>
        {qrVerify ? (
          <div className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-950 space-y-1">
            <p className="font-semibold">Scanned recipient — verify before paying</p>
            <p>
              <span className="text-indigo-800/80">Name:</span>{' '}
              <span className="font-medium">{qrVerify.name}</span>
            </p>
            <p>
              <span className="text-indigo-800/80">Phone:</span>{' '}
              <span className="font-mono font-medium">{qrVerify.phone}</span>
            </p>
            <p>
              <span className="text-indigo-800/80">Account number:</span>{' '}
              <span className="font-mono font-medium">{qrVerify.accountNumber}</span>
            </p>
          </div>
        ) : null}

        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary" htmlFor="source-account">
            Source account
          </label>
          <select
            className="min-h-[44px] w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none"
            id="source-account"
            value={sourceAccountNumber}
            onChange={(event) => setSourceAccountNumber(event.target.value)}
            required
            disabled={executeMutation.isPending}
          >
            <option value="">Select account</option>
            {accountsQuery.data?.map((account) => (
              <option
                disabled={account.status !== 'ACTIVE'}
                key={account.id}
                value={account.accountNumber}
              >
                {account.label} - {account.currency} {account.balance.toLocaleString()}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary" htmlFor="destination-account">
            Destination phone number
          </label>
          <Input
            disabled={executeMutation.isPending}
            id="destination-account"
            inputMode="tel"
            placeholder="+252771000011"
            value={destinationPhoneNumber}
            onChange={(event) =>
              setDestinationPhoneNumber(event.target.value.replace(/[^\d+]/g, ''))
            }
            required
          />
          {recipientQuery.isFetching ? (
            <p className="text-xs text-text-tertiary">Looking up recipient…</p>
          ) : recipientName ? (
            <p className="text-xs text-text-secondary">Recipient: <span className="font-semibold text-text-primary">{recipientName}</span></p>
          ) : recipientNotFound && normalizedPhone ? (
            <p className="text-xs text-brand-danger">Customer not found.</p>
          ) : null}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary" htmlFor="amount">
            Amount
          </label>
          <Input
            disabled={executeMutation.isPending}
            id="amount"
            inputMode="decimal"
            placeholder="500.00"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            required
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary" htmlFor="description">
            Description
          </label>
          <Input
            disabled={executeMutation.isPending}
            id="description"
            placeholder="Optional note"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary" htmlFor="pin">
            Transaction PIN
          </label>
          <Input
            id="pin"
            type="password"
            inputMode="numeric"
            maxLength={6}
            placeholder="••••"
            value={pin}
            onChange={(event) => setPin(event.target.value.replace(/\D/g, '').slice(0, 6))}
            required
            disabled={executeMutation.isPending}
          />
        </div>

        {error ? <p className="text-sm text-brand-danger">{error}</p> : null}
        <p className="text-xs text-text-tertiary">Attempt key: {idempotencyKey}</p>

        <Button
          className="w-full"
          loading={executeMutation.isPending}
          type="submit"
          disabled={recipientNotFound || recipientQuery.isFetching}
        >
          Submit transfer
        </Button>
      </Card>
      )}
    </div>
  )
}
