import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card } from '../../../shared/components/ui/Card'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
import { Input } from '../../../shared/components/ui/Input'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { normalizeApiError } from '../../../core/api/error-normalizer'
import { getSessionState, updateSessionState } from '../../../core/state/auth-state'
import { getKycStatus, uploadKycDocument } from '../services/kyc-service'
import type { KycDocumentType, KycStatus } from '../types'

const documentTypes: Array<{ label: string; value: KycDocumentType }> = [
  { label: 'National ID', value: 'NATIONAL_ID' },
  { label: 'Passport', value: 'PASSPORT' },
  { label: 'Residence Permit', value: 'RESIDENCE_PERMIT' },
  { label: 'Selfie / Liveness Photo', value: 'SELFIE' },
  { label: 'Proof of Address', value: 'PROOF_OF_ADDRESS' },
]

function getStatusVariant(status: KycStatus) {
  if (status === 'APPROVED') return 'success'
  if (status === 'REJECTED') return 'danger'
  if (status === 'PENDING') return 'warning'
  return 'info'
}

export function KycStatusPage() {
  const queryClient = useQueryClient()
  const [documentType, setDocumentType] = useState<KycDocumentType>('NATIONAL_ID')
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)

  const statusQuery = useQuery({
    queryKey: ['kyc-status'],
    queryFn: getKycStatus,
  })

  useEffect(() => {
    const user = getSessionState().user
    const nextStatus = statusQuery.data?.kycStatus

    if (user && nextStatus && user.kycStatus !== nextStatus) {
      updateSessionState({ user: { ...user, kycStatus: nextStatus } })
    }
  }, [statusQuery.data?.kycStatus])

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error('Select a document before uploading.')
      return uploadKycDocument(documentType, file)
    },
    onSuccess: async () => {
      setError(null)
      setFile(null)
      await queryClient.invalidateQueries({ queryKey: ['kyc-status'] })
    },
    onError: (nextError) => setError(normalizeApiError(nextError).detail),
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    uploadMutation.mutate()
  }

  const kycStatus = statusQuery.data?.kycStatus ?? 'NOT_SUBMITTED'
  const canUpload = kycStatus !== 'APPROVED' && kycStatus !== 'PENDING'

  return (
    <div className="max-w-xl space-y-4">
        {statusQuery.isLoading ? (
          <Skeleton className="h-32 w-full" />
        ) : (
          <Card className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-text-secondary">Current status</span>
              <Badge variant={getStatusVariant(kycStatus)}>{kycStatus.replace('_', ' ')}</Badge>
            </div>
            <p className="text-sm text-text-secondary">
              {kycStatus === 'APPROVED'
                ? 'Financial actions are enabled.'
                : 'Financial actions remain unavailable until approval.'}
            </p>
          </Card>
        )}

        {canUpload ? (
          <Card as="form" className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-secondary" htmlFor="document-type">
                Document type
              </label>
              <select
                className="min-h-[44px] w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none"
                id="document-type"
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value as KycDocumentType)}
              >
                {documentTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-secondary" htmlFor="kyc-file">
                Upload document
              </label>
              <Input
                id="kyc-file"
                type="file"
                accept="image/*,.pdf"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                required
              />
            </div>
            {error ? <p className="text-sm text-brand-danger">{error}</p> : null}
            <Button className="w-full" loading={uploadMutation.isPending} type="submit">
              Submit for review
            </Button>
          </Card>
        ) : null}

        <Card className="space-y-3">
          <h2 className="text-base font-semibold text-text-primary">Documents</h2>
          {statusQuery.data?.documents.length ? (
            <div className="divide-y divide-border">
              {statusQuery.data.documents.map((document) => (
                <div key={document.id} className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      {document.documentType.replaceAll('_', ' ')}
                    </p>
                    {document.rejectionReason ? (
                      <p className="text-xs text-brand-danger">{document.rejectionReason}</p>
                    ) : null}
                  </div>
                  <Badge variant={document.status === 'APPROVED' ? 'success' : document.status === 'REJECTED' ? 'danger' : 'warning'}>
                    {document.status}
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-tertiary">No documents uploaded yet.</p>
          )}
        </Card>
    </div>
  )
}
