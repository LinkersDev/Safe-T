import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Card } from '../../../shared/components/ui/Card'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { lookupCustomerByPhone } from '../services/teller-service'
import { normalizeApiError } from '../../../core/api/error-normalizer'

export function TellerCustomerLookupPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [phone, setPhone] = useState('')

  const mutation = useMutation({
    mutationFn: () => lookupCustomerByPhone(phone.trim()),
    onSuccess: (data) => {
      toast.success('Customer found.')
      navigate(ROUTE_PATHS.staffTellerCustomerProfile(data.user_id))
    },
    onError: (err) => {
      const normalized = normalizeApiError(err)
      toast.error(normalized.detail)
    },
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    mutation.mutate()
  }

  return (
    <div className="max-w-lg space-y-4">
      <Card as="form" className="space-y-3" onSubmit={onSubmit}>
        <p className="text-sm font-semibold text-text-primary">Customer lookup</p>
        <p className="text-xs text-text-tertiary">
          Enter the customer phone number to open their profile and complete KYC info.
        </p>
        <Input
          inputMode="tel"
          placeholder="Phone (+E.164)"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          required
        />
        <Button loading={mutation.isPending} type="submit" variant="secondary">
          Open profile
        </Button>
      </Card>

      <StatusNoticeCard
        title="Tip"
        variant="info"
        message="If KYC approval fails in Admin, it usually means the customer is missing KYC Profile fields. Use this lookup to complete them."
      />
    </div>
  )
}

