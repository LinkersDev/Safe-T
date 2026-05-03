import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Card } from '../../../shared/components/ui/Card'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import { tellerDeposit } from '../services/teller-service'
import { normalizeApiError } from '../../../core/api/error-normalizer'

export function TellerDepositPage() {
  const toast = useToast()
  const [lookup, setLookup] = useState('')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')

  const mutation = useMutation({
    mutationFn: tellerDeposit,
    onSuccess: () => toast.success('Deposit processed.'),
    onError: (err) => toast.error(normalizeApiError(err).detail),
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    mutation.mutate({
      lookup: lookup.trim(),
      amount: amount.trim(),
      description: description.trim() || undefined,
    })
  }

  return (
    <div className="max-w-lg space-y-4">
      <Card as="form" className="space-y-3" onSubmit={onSubmit}>
        <Input placeholder="Phone (+E.164) or 16-digit account number" value={lookup} onChange={(e) => setLookup(e.target.value)} required />
        <Input inputMode="decimal" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        <Input placeholder="Description (optional)" value={description} onChange={(e) => setDescription(e.target.value)} />
        <Button loading={mutation.isPending} type="submit">
          Deposit
        </Button>
      </Card>

      {mutation.data && (
        <StatusNoticeCard
          title="Deposit created"
          message={`Reference ${mutation.data.transaction.reference_number} · ${mutation.data.transaction.status}`}
          variant="info"
        />
      )}
    </div>
  )
}

