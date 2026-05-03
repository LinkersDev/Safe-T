import { useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { Card } from '../../../shared/components/ui/Card'
import { Button } from '../../../shared/components/ui/Button'
import { Input } from '../../../shared/components/ui/Input'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import { getCustomerProfile, submitCustomerKycProfile, uploadCustomerKycDocument } from '../services/teller-service'

export function TellerCustomerProfilePage() {
  const toast = useToast()
  const qc = useQueryClient()
  const params = useParams()
  const userId = params.userId ?? ''

  const profileQuery = useQuery({
    queryKey: ['teller-customer-profile', userId],
    queryFn: () => getCustomerProfile(userId),
    enabled: Boolean(userId),
  })

  const data = profileQuery.data
  const completeness = data?.kyc?.completeness

  const [legalFullName, setLegalFullName] = useState('')
  const [dateOfBirth, setDateOfBirth] = useState('')
  const [nationality, setNationality] = useState('')
  const [idType, setIdType] = useState<'NATIONAL_ID' | 'PASSPORT' | 'RESIDENCE_PERMIT'>('NATIONAL_ID')
  const [idNumber, setIdNumber] = useState('')
  const [addressLine1, setAddressLine1] = useState('')
  const [addressCity, setAddressCity] = useState('')
  const [addressCountry, setAddressCountry] = useState('')

  const canPrefill = useMemo(() => {
    const p = data?.kyc?.profile
    return Boolean(p && typeof p === 'object')
  }, [data?.kyc?.profile])

  const submitProfile = useMutation({
    mutationFn: async () =>
      submitCustomerKycProfile(userId, {
        legal_full_name: legalFullName.trim(),
        date_of_birth: dateOfBirth,
        nationality: nationality.trim(),
        id_type: idType,
        id_number: idNumber.trim(),
        address_line1: addressLine1.trim(),
        address_city: addressCity.trim(),
        address_country: addressCountry.trim(),
      }),
    onSuccess: async () => {
      toast.success('KYC profile saved (pending review).')
      await qc.invalidateQueries({ queryKey: ['teller-customer-profile', userId] })
    },
    onError: () => toast.error('Failed to save KYC profile.'),
  })

  const [docType, setDocType] = useState<'NATIONAL_ID' | 'PASSPORT' | 'RESIDENCE_PERMIT' | 'PROOF_OF_ADDRESS' | 'SELFIE'>('NATIONAL_ID')
  const [docFile, setDocFile] = useState<File | null>(null)

  const uploadDoc = useMutation({
    mutationFn: async () => {
      if (!docFile) throw new Error('Missing file')
      return uploadCustomerKycDocument(userId, { document_type: docType, file: docFile })
    },
    onSuccess: async () => {
      toast.success('Document uploaded (pending review).')
      setDocFile(null)
      await qc.invalidateQueries({ queryKey: ['teller-customer-profile', userId] })
    },
    onError: () => toast.error('Failed to upload document.'),
  })

  function onSubmitProfile(e: FormEvent) {
    e.preventDefault()
    submitProfile.mutate()
  }

  function onUploadDoc(e: FormEvent) {
    e.preventDefault()
    if (!docFile) return toast.warning('Choose a file first.')
    uploadDoc.mutate()
  }

  if (profileQuery.isLoading) {
    return <div className="max-w-3xl p-4">Loading…</div>
  }

  if (profileQuery.isError || !data) {
    return <div className="max-w-3xl p-4">Failed to load customer.</div>
  }

  return (
    <div className="max-w-3xl space-y-4">
      <Card className="space-y-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <p className="text-sm font-semibold">{data.user.full_name}</p>
            <p className="text-xs text-text-secondary">{data.user.phone_number}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-text-secondary">User status</p>
            <p className="text-sm font-semibold">{data.user.status}</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <div>
            <p className="text-xs text-text-secondary">KYC status</p>
            <p className="text-sm font-semibold">{data.user.kyc_status}</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">Completeness</p>
            <p className="text-sm font-semibold">{completeness?.is_valid ? 'Complete' : 'Incomplete'}</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">Accounts</p>
            <p className="text-sm font-semibold">{data.accounts?.length ?? 0}</p>
          </div>
        </div>

        {!completeness?.is_valid && (
          <StatusNoticeCard
            title="Next steps"
            variant="warning"
            message={`Missing fields: ${(completeness?.missing_fields ?? []).join(', ') || '—'} · Missing documents: ${(completeness?.missing_documents ?? []).join(', ') || '—'}`}
          />
        )}
      </Card>

      <Card className="space-y-3">
        <p className="text-sm font-semibold">KYC profile (optional — helps approval)</p>
        {!data.kyc.profile ? (
          <p className="text-xs text-text-secondary">No profile submitted yet.</p>
        ) : (
          <p className="text-xs text-text-secondary">Profile exists. You can re-submit to update.</p>
        )}

        <form className="grid grid-cols-1 gap-3 sm:grid-cols-2" onSubmit={onSubmitProfile}>
          <Input placeholder="Legal full name" value={legalFullName} onChange={(e) => setLegalFullName(e.target.value)} required />
          <Input type="date" value={dateOfBirth} onChange={(e) => setDateOfBirth(e.target.value)} required />
          <Input placeholder="Nationality" value={nationality} onChange={(e) => setNationality(e.target.value)} required />
          <Input placeholder="ID type (NATIONAL_ID / PASSPORT / RESIDENCE_PERMIT)" value={idType} onChange={(e) => setIdType(e.target.value as any)} required />
          <Input placeholder="ID number" value={idNumber} onChange={(e) => setIdNumber(e.target.value)} required />
          <Input placeholder="Address line 1" value={addressLine1} onChange={(e) => setAddressLine1(e.target.value)} required />
          <Input placeholder="City" value={addressCity} onChange={(e) => setAddressCity(e.target.value)} required />
          <Input placeholder="Country" value={addressCountry} onChange={(e) => setAddressCountry(e.target.value)} required />

          <div className="sm:col-span-2 flex flex-wrap gap-2">
            <Button loading={submitProfile.isPending} type="submit">
              Save KYC profile
            </Button>
            {canPrefill && (
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  const p: any = data.kyc.profile
                  setLegalFullName(p?.legal_full_name ?? '')
                  setDateOfBirth((p?.date_of_birth ?? '').slice(0, 10))
                  setNationality(p?.nationality ?? '')
                  setIdType((p?.id_type ?? 'NATIONAL_ID') as any)
                  setIdNumber(p?.id_number ?? '')
                  setAddressLine1(p?.address_line1 ?? '')
                  setAddressCity(p?.address_city ?? '')
                  setAddressCountry(p?.address_country ?? '')
                }}
              >
                Prefill from existing
              </Button>
            )}
          </div>
        </form>
      </Card>

      <Card className="space-y-3">
        <p className="text-sm font-semibold">Documents</p>
        {data.kyc.documents?.length ? (
          <div className="space-y-2">
            {data.kyc.documents.map((d: any) => (
              <div key={String(d.id ?? d.file)} className="flex items-center justify-between gap-2 rounded-lg border border-border px-3 py-2">
                <div>
                  <p className="text-xs font-semibold">{d.document_type}</p>
                  <p className="text-[11px] text-text-secondary">{d.status}</p>
                </div>
                <p className="text-[11px] text-text-secondary">{String(d.created_at ?? '')}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-secondary">No documents uploaded yet.</p>
        )}

        <form className="space-y-2" onSubmit={onUploadDoc}>
          <Input
            placeholder="Document type (NATIONAL_ID / PASSPORT / RESIDENCE_PERMIT / PROOF_OF_ADDRESS / SELFIE)"
            value={docType}
            onChange={(e) => setDocType(e.target.value as any)}
          />
          <input
            type="file"
            onChange={(e) => setDocFile(e.target.files?.[0] ?? null)}
          />
          <div>
            <Button loading={uploadDoc.isPending} type="submit">
              Upload document
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}

