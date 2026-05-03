import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Card } from '../../../shared/components/ui/Card'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import { registerCustomer } from '../services/teller-service'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { normalizeApiError } from '../../../core/api/error-normalizer'

export function TellerRegisterCustomerPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [legalFullName, setLegalFullName] = useState('')
  const [dateOfBirth, setDateOfBirth] = useState('')
  const [nationality, setNationality] = useState('')
  const [idType, setIdType] = useState<'NATIONAL_ID' | 'PASSPORT' | 'RESIDENCE_PERMIT'>('NATIONAL_ID')
  const [idNumber, setIdNumber] = useState('')
  const [addressLine1, setAddressLine1] = useState('')
  const [addressCity, setAddressCity] = useState('')
  const [addressCountry, setAddressCountry] = useState('')
  const [documentType, setDocumentType] = useState<'NATIONAL_ID' | 'PASSPORT' | 'RESIDENCE_PERMIT'>('NATIONAL_ID')
  const [documentFile, setDocumentFile] = useState<File | null>(null)
  const [created, setCreated] = useState<Awaited<ReturnType<typeof registerCustomer>> | null>(null)

  const mutation = useMutation({
    mutationFn: registerCustomer,
    onSuccess: (data) => {
      toast.success('Customer registered.')
      setCreated(data)
      // Clear form immediately to speed up registering multiple customers.
      setFullName('')
      setPhoneNumber('')
      setLegalFullName('')
      setDateOfBirth('')
      setNationality('')
      setIdType('NATIONAL_ID')
      setIdNumber('')
      setAddressLine1('')
      setAddressCity('')
      setAddressCountry('')
      setDocumentType('NATIONAL_ID')
      setDocumentFile(null)
    },
    onError: (err) => {
      const normalized = normalizeApiError(err)
      const payload = (err as any)?.response?.data as any
      if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
        // DRF serializer errors often come as { field: ["msg"] }
        const firstField = Object.keys(payload)[0]
        const firstVal = payload[firstField]
        const msg = Array.isArray(firstVal) ? String(firstVal[0]) : String(firstVal)
        toast.error(`${firstField}: ${msg}`)
        return
      }
      toast.error(normalized.detail || 'Failed to register customer.')
    },
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!documentFile) {
      toast.warning('Please upload an ID document file.')
      return
    }
    // Some browsers don’t enforce <input type="date">. Backend expects YYYY-MM-DD.
    if (dateOfBirth && !/^\d{4}-\d{2}-\d{2}$/.test(dateOfBirth)) {
      toast.warning('Date of birth must be in YYYY-MM-DD format.')
      return
    }
    mutation.mutate({
      full_name: fullName.trim(),
      phone_number: phoneNumber.trim(),
      legal_full_name: legalFullName.trim(),
      date_of_birth: dateOfBirth,
      nationality: nationality.trim(),
      id_type: idType,
      id_number: idNumber.trim(),
      address_line1: addressLine1.trim(),
      address_city: addressCity.trim(),
      address_country: addressCountry.trim(),
      document_type: documentType,
      file: documentFile,
    })
  }

  const result = created

  return (
    <div className="max-w-lg space-y-4">
      <Card as="form" className="space-y-3" onSubmit={onSubmit}>
        <Input placeholder="Customer full name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
        <Input inputMode="tel" placeholder="Phone (+E.164)" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} required />
        <div className="pt-2">
          <p className="text-xs font-semibold text-text-secondary">KYC profile (required)</p>
        </div>
        <Input placeholder="Legal full name (as ID)" value={legalFullName} onChange={(e) => setLegalFullName(e.target.value)} required />
        <Input type="date" value={dateOfBirth} onChange={(e) => setDateOfBirth(e.target.value)} required />
        <Input placeholder="Nationality" value={nationality} onChange={(e) => setNationality(e.target.value)} required />
        <select
          value={idType}
          onChange={(e) => setIdType(e.target.value as any)}
          className="min-h-[44px] w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none transition-colors focus:border-brand-primary"
          required
        >
          <option value="NATIONAL_ID">NATIONAL_ID</option>
          <option value="PASSPORT">PASSPORT</option>
          <option value="RESIDENCE_PERMIT">RESIDENCE_PERMIT</option>
        </select>
        <Input placeholder="ID number" value={idNumber} onChange={(e) => setIdNumber(e.target.value)} required />
        <Input placeholder="Address line 1" value={addressLine1} onChange={(e) => setAddressLine1(e.target.value)} required />
        <Input placeholder="City" value={addressCity} onChange={(e) => setAddressCity(e.target.value)} required />
        <Input placeholder="Country" value={addressCountry} onChange={(e) => setAddressCountry(e.target.value)} required />

        <div className="pt-2">
          <p className="text-xs font-semibold text-text-secondary">ID document (required)</p>
        </div>
        <select
          value={documentType}
          onChange={(e) => setDocumentType(e.target.value as any)}
          className="min-h-[44px] w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none transition-colors focus:border-brand-primary"
          required
        >
          <option value="NATIONAL_ID">NATIONAL_ID</option>
          <option value="PASSPORT">PASSPORT</option>
          <option value="RESIDENCE_PERMIT">RESIDENCE_PERMIT</option>
        </select>
        <input
          type="file"
          onChange={(e) => setDocumentFile(e.target.files?.[0] ?? null)}
          className="w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary"
          required
        />
        <Button loading={mutation.isPending} type="submit">
          Create customer
        </Button>
      </Card>

      {result && (
        <div className="space-y-3">
          <StatusNoticeCard
            title="Customer created"
            message={`Account ${result.account?.account_number ?? '—'} · ${result.onboarding?.next_step ?? 'Customer must complete first login setup.'}`}
            variant="info"
          />
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" onClick={() => setCreated(null)}>
              Dismiss
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

