import { useState, type FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import { DevOtpCard } from '../../../shared/components/ui/DevOtpCard'
import { Input } from '../../../shared/components/ui/Input'
import { PaymentResultCard } from '../../../shared/components/financial/PaymentResultCard'
import { createIdempotencyKey } from '../../../core/api/idempotency'
import { normalizeApiError } from '../../../core/api/error-normalizer'
import { getReconciliationMessage, shouldReconcilePayment } from '../../../core/api/reconciliation'
import { getAccounts } from '../../accounts/services/account-service'
import {
  executeBillPayment,
  fetchBill,
  getBillProviders,
  requestBillPaymentOtp,
} from '../services/bill-payment-service'
import type { BillInfo, BillPayResult } from '../types'

type BillStep = 'fetch' | 'confirm' | 'otp' | 'result'

export function BillPaymentPage() {
  const [step, setStep] = useState<BillStep>('fetch')
  const [providerCode, setProviderCode] = useState('')
  const [serviceNumber, setServiceNumber] = useState('')
  const [sourceAccountNumber, setSourceAccountNumber] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [devOtp, setDevOtp] = useState<string | null>(null)
  const [idempotencyKey, setIdempotencyKey] = useState(createIdempotencyKey)
  const [billInfo, setBillInfo] = useState<BillInfo | null>(null)
  const [result, setResult] = useState<BillPayResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const accountsQuery = useQuery({ queryKey: ['accounts'], queryFn: getAccounts })
  const providersQuery = useQuery({ queryKey: ['bill-providers'], queryFn: getBillProviders })

  const fetchMutation = useMutation({
    mutationFn: () => fetchBill(providerCode, serviceNumber),
    onSuccess: (bill) => {
      setBillInfo(bill)
      setError(null)
      setStep('confirm')
    },
    onError: (nextError) => {
      const normalized = normalizeApiError(nextError)
      setError(
        shouldReconcilePayment(normalized.status)
          ? getReconciliationMessage(normalized.detail)
          : normalized.detail,
      )
    },
  })

  const otpMutation = useMutation({
    mutationFn: () => requestBillPaymentOtp(providerCode, serviceNumber),
    onSuccess: (response) => {
      setError(null)
      const otp = response.dev_otp ?? response._debug_otp ?? null
      setDevOtp(otp)
      setStep('otp')
    },
    onError: (nextError) => setError(normalizeApiError(nextError).detail),
  })

  const executeMutation = useMutation({
    mutationFn: executeBillPayment,
    onSuccess: (transaction) => {
      setResult(transaction)
      setError(null)
      setStep('result')
    },
    onError: (nextError) => setError(normalizeApiError(nextError).detail),
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    if (step === 'fetch') {
      fetchMutation.mutate()
      return
    }

    if (step === 'confirm') {
      otpMutation.mutate()
      return
    }

    if (!billInfo) {
      setError('Bill details are missing. Fetch the bill again.')
      return
    }

    executeMutation.mutate({
      providerCode,
      serviceNumber,
      billReference: billInfo.bill_reference,
      sourceAccountNumber,
      amount: billInfo.amount,
      otpCode,
      idempotencyKey,
    })
  }

  function resetBillPayment() {
    setStep('fetch')
    setProviderCode('')
    setServiceNumber('')
    setSourceAccountNumber('')
    setOtpCode('')
    setDevOtp(null)
    setIdempotencyKey(createIdempotencyKey())
    setBillInfo(null)
    setResult(null)
    setError(null)
  }

  return (
    <div className="max-w-xl">
      {step === 'result' && result ? (
        <div className="space-y-4">
          <PaymentResultCard transaction={result} />
          <Button className="w-full" onClick={resetBillPayment}>
            New bill payment
          </Button>
        </div>
      ) : (
        <Card as="form" className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-sm font-medium text-text-secondary" htmlFor="provider">
              Provider
            </label>
            <select
              className="min-h-[44px] w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none"
              disabled={step !== 'fetch'}
              id="provider"
              value={providerCode}
              onChange={(event) => setProviderCode(event.target.value)}
              required
            >
              <option value="">Select provider</option>
              {providersQuery.data?.map((provider) => (
                <option key={provider.code} value={provider.code}>
                  {provider.name} ({provider.serviceType})
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-text-secondary" htmlFor="service-number">
              Service number
            </label>
            <Input
              disabled={step !== 'fetch'}
              id="service-number"
              value={serviceNumber}
              onChange={(event) => setServiceNumber(event.target.value)}
              required
            />
          </div>

          {billInfo ? (
            <Card className="space-y-1 bg-surface-secondary shadow-none">
              <p className="font-semibold">
                Bill: USD {Number(billInfo.amount).toLocaleString()}
              </p>
              <p className="font-mono text-xs text-text-tertiary">{billInfo.bill_reference}</p>
            </Card>
          ) : null}

          {step !== 'fetch' ? (
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-secondary" htmlFor="bill-source">
                Source account
              </label>
              <select
                className="min-h-[44px] w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none"
                id="bill-source"
                value={sourceAccountNumber}
                onChange={(event) => setSourceAccountNumber(event.target.value)}
                required
                disabled={step === 'otp'}
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
          ) : null}

          {step === 'otp' ? (
            <div className="space-y-2">
              {devOtp ? <DevOtpCard otp={devOtp} /> : null}
              <label className="text-sm font-medium text-text-secondary" htmlFor="bill-otp">
                OTP code
              </label>
              <Input
                id="bill-otp"
                inputMode="numeric"
                maxLength={6}
                value={otpCode}
                onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                required
              />
            </div>
          ) : null}

          {error ? <p className="text-sm text-brand-danger">{error}</p> : null}
          <p className="text-xs text-text-tertiary">Attempt key: {idempotencyKey}</p>
          <Button
            className="w-full"
            loading={fetchMutation.isPending || otpMutation.isPending || executeMutation.isPending}
            type="submit"
          >
            {step === 'fetch' ? 'Fetch bill' : step === 'confirm' ? 'Request OTP' : 'Pay bill'}
          </Button>
        </Card>
      )}
    </div>
  )
}
