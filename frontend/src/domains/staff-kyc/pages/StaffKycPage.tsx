import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
import { DataTable, type Column } from '../../../shared/components/ui/DataTable'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { ConfirmationModal } from '../../../shared/components/ui/ConfirmationModal'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import { normalizeApiError } from '../../../core/api/error-normalizer'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import {
  approveKycUser,
  getPendingKycUsers,
  rejectKycUser,
  getStaffKycUserDocuments,
  approveKycDocument,
  rejectKycDocument,
  type StaffKycDocument,
} from '../../staff/services/staff-service'
import type { KycReviewUser } from '../../staff/types'

export function StaffKycPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [expandedUserId, setExpandedUserId] = useState<number | null>(null)
  const [rejectDocTarget, setRejectDocTarget] = useState<StaffKycDocument | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  const kycQuery = useQuery({ queryKey: ['staff-pending-kyc'], queryFn: getPendingKycUsers })

  const docsQuery = useQuery({
    queryKey: ['staff-kyc-docs', expandedUserId],
    queryFn: () => getStaffKycUserDocuments(expandedUserId!),
    enabled: expandedUserId != null,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['staff-pending-kyc'] })

  const approveMutation = useMutation({
    mutationFn: approveKycUser,
    onSuccess: () => { invalidate(); toast.success('KYC approved.') },
    onError: (err) => {
      const normalized = normalizeApiError(err)
      const payload = (err as any)?.response?.data as any
      if (normalized.status === 400 && payload?.missing_fields) {
        toast.warning(
          `KYC incomplete. Missing fields: ${(payload.missing_fields ?? []).join(', ') || '—'} · Missing documents: ${(payload.missing_documents ?? []).join(', ') || '—'}`,
        )
        return
      }
      toast.error(normalized.detail || 'Failed to approve.')
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (userId: number) => rejectKycUser(userId, 'Rejected by KYC review.'),
    onSuccess: () => { invalidate(); toast.success('KYC rejected.') },
    onError: () => toast.error('Failed to reject.'),
  })

  const approveDocMutation = useMutation({
    mutationFn: (docId: number) => approveKycDocument(docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff-kyc-docs', expandedUserId] })
      invalidate()
      toast.success('Document approved.')
    },
    onError: () => toast.error('Failed to approve document.'),
  })

  const rejectDocMutation = useMutation({
    mutationFn: ({ docId, reason }: { docId: number; reason: string }) =>
      rejectKycDocument(docId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff-kyc-docs', expandedUserId] })
      invalidate()
      setRejectDocTarget(null)
      setRejectReason('')
      toast.success('Document rejected.')
    },
    onError: () => toast.error('Failed to reject document.'),
  })

  const columns: Column<KycReviewUser>[] = [
    {
      key: 'user',
      header: 'Applicant',
      render: (u) => (
        <div>
          <p className="font-semibold text-text-primary">{u.fullName}</p>
          <p className="text-xs text-text-tertiary">{u.phoneNumber}</p>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (u) => (
        <Badge variant={u.kycStatus === 'PENDING' ? 'warning' : 'info'}>{u.kycStatus}</Badge>
      ),
    },
    {
      key: 'docs',
      header: 'Pending docs',
      render: (u) => (
        <Badge variant="warning">
          {u.pendingDocumentCount} document{u.pendingDocumentCount !== 1 ? 's' : ''}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (u) => (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            className="!min-h-0 px-3 py-1.5 text-xs"
            onClick={(e) => {
              e.stopPropagation()
              setExpandedUserId(expandedUserId === u.id ? null : u.id)
            }}
            variant="secondary"
          >
            {expandedUserId === u.id ? 'Close docs' : 'Review docs'}
          </Button>
          <Button
            className="!min-h-0 px-3 py-1.5 text-xs"
            onClick={(e) => { e.stopPropagation(); approveMutation.mutate(u.id) }}
            disabled={approveMutation.isPending}
          >
            Approve All
          </Button>
          <a
            className="rounded-lg border border-border bg-surface-secondary px-3 py-1.5 text-xs font-semibold text-text-primary hover:bg-surface-tertiary"
            href={ROUTE_PATHS.staffTellerCustomerProfile(u.id)}
            onClick={(e) => e.stopPropagation()}
          >
            Open profile
          </a>
          <Button
            className="!min-h-0 px-3 py-1.5 text-xs"
            onClick={(e) => { e.stopPropagation(); rejectMutation.mutate(u.id) }}
            variant="danger"
            disabled={rejectMutation.isPending}
          >
            Reject
          </Button>
        </div>
      ),
    },
  ]

  if (kycQuery.isLoading) {
    return <Skeleton className="h-64 w-full rounded-xl" />
  }

  if (kycQuery.isError) {
    return (
      <StatusNoticeCard
        title="KYC queue unavailable"
        message="KYC applications could not be loaded. Please retry."
        variant="error"
      />
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-tertiary">
        {kycQuery.data?.length ?? 0} applications in queue
      </p>

      <DataTable
        columns={columns}
        rows={kycQuery.data ?? []}
        keyExtractor={(u) => u.id}
        emptyMessage="KYC queue is empty — no pending applications."
      />

      {/* Per-document panel */}
      {expandedUserId != null && (
        <div className="rounded-xl border border-border bg-surface-primary p-5">
          <h3 className="mb-4 font-semibold text-text-primary">
            Documents for user #{expandedUserId}
          </h3>
          {docsQuery.isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full rounded-lg" />
              ))}
            </div>
          ) : docsQuery.data?.length === 0 ? (
            <p className="text-sm text-text-secondary">No documents found.</p>
          ) : docsQuery.isError ? (
            <StatusNoticeCard
              title="Document fetch failed"
              message="Unable to load user documents right now."
              variant="warning"
            />
          ) : (
            <div className="space-y-3">
              {docsQuery.data?.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between gap-4 rounded-lg border border-border p-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-text-primary">
                      {doc.documentType.replace(/_/g, ' ')}
                    </p>
                    <p className="text-xs text-text-tertiary">
                      Submitted: {doc.submittedAt ? new Date(doc.submittedAt).toLocaleDateString() : '—'}
                    </p>
                    {doc.rejectionReason && (
                      <p className="text-xs text-rose-500">Reason: {doc.rejectionReason}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        doc.status === 'APPROVED' ? 'success' :
                        doc.status === 'REJECTED' ? 'danger' : 'warning'
                      }
                    >
                      {doc.status}
                    </Badge>
                    {doc.fileUrl && (
                      <a
                        href={doc.fileUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-lg border border-border bg-surface-secondary px-2.5 py-1 text-xs font-semibold text-text-primary hover:bg-surface-tertiary"
                      >
                        View
                      </a>
                    )}
                    {doc.status === 'PENDING' && (
                      <>
                        <Button
                          className="!min-h-0 px-2.5 py-1 text-xs"
                          onClick={() => approveDocMutation.mutate(doc.id)}
                          disabled={approveDocMutation.isPending}
                        >
                          Approve
                        </Button>
                        <Button
                          className="!min-h-0 px-2.5 py-1 text-xs"
                          variant="danger"
                          onClick={() => setRejectDocTarget(doc)}
                        >
                          Reject
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {rejectDocTarget && (
        <ConfirmationModal
          title="Reject document"
          description={`Reject "${rejectDocTarget.documentType.replace(/_/g, ' ')}"?`}
          confirmLabel="Reject"
          variant="danger"
          loading={rejectDocMutation.isPending}
          onConfirm={() =>
            rejectDocMutation.mutate({
              docId: rejectDocTarget.id,
              reason: rejectReason || 'Document does not meet requirements.',
            })
          }
          onCancel={() => { setRejectDocTarget(null); setRejectReason('') }}
        >
          <div className="mt-3">
            <label className="mb-1 block text-xs font-medium text-text-secondary">Rejection reason</label>
            <input
              type="text"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Document unclear, expired, etc."
              className="w-full rounded-lg border border-border bg-surface-secondary px-3 py-2 text-sm text-text-primary outline-none focus:border-rose-400"
            />
          </div>
        </ConfirmationModal>
      )}
    </div>
  )
}
