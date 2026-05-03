import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import { Input } from '../../../shared/components/ui/Input'
import { ConfirmationModal } from '../../../shared/components/ui/ConfirmationModal'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import { useAuthSession } from '../../security/hooks/useAuthSession'
import {
  blockStaffAccount,
  freezeStaffAccount,
  unfreezeStaffAccount,
  closeStaffAccount,
  getStaffAccount,
  unblockStaffAccount,
} from '../services/staff-account-service'
import type { StaffAccountDetails } from '../services/staff-account-service'
import { getCustomerProfile } from '../../teller/services/teller-service'

type ActionType = 'freeze' | 'unfreeze' | 'block' | 'unblock' | 'close' | null

export function StaffAccountsPage() {
  const [lookupValue, setLookupValue] = useState('')
  const [reason, setReason] = useState('')
  const [account, setAccount] = useState<StaffAccountDetails | null>(null)
  const [pendingAction, setPendingAction] = useState<ActionType>(null)
  const toast = useToast()
  const { permissions } = useAuthSession()

  const canFreeze = permissions.includes('freeze_account')
  const canUnfreeze = permissions.includes('unfreeze_account')
  const canBlock = permissions.includes('block_account')
  const canAnyRestriction = canFreeze || canUnfreeze || canBlock
  const canReviewKyc = permissions.includes('review_kyc')

  const lookupMutation = useMutation({
    mutationFn: getStaffAccount,
    onSuccess: setAccount,
    onError: () => toast.error('Account not found.'),
  })

  function execAction(action: ActionType) {
    const staffAccountId = account?.id
    if (!action || !staffAccountId) return
    const r = reason.trim() || 'Staff account review.'
    const handlers: Record<NonNullable<ActionType>, () => Promise<unknown>> = {
      freeze:   () => freezeStaffAccount(staffAccountId, r),
      unfreeze: () => unfreezeStaffAccount(staffAccountId, r),
      block:    () => blockStaffAccount(staffAccountId, r),
      unblock:  () => unblockStaffAccount(staffAccountId, r),
      close:    () => closeStaffAccount(staffAccountId, r),
    }
    handlers[action]()
      .then(() => {
        setPendingAction(null)
        toast.success(`Account ${action}d successfully.`)
        lookupMutation.mutate(lookupValue)
      })
      .catch(() => toast.error(`Failed to ${action} account.`))
  }

  function handleLookup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    lookupMutation.mutate(lookupValue)
  }

  const isFrozen = account?.status === 'FROZEN'
  const isBlocked = account?.status === 'BLOCKED'
  const isClosed = account?.status === 'CLOSED'

  const ownerId = account?.owner?.id
  const customerQuery = useQuery({
    queryKey: ['staff-account-owner-profile', ownerId],
    queryFn: () => getCustomerProfile(ownerId!),
    enabled: Boolean(ownerId),
  })

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          <Card as="form" className="space-y-3" onSubmit={handleLookup}>
            <Input
              inputMode="tel"
              placeholder="Phone (+E.164), account number, or account id"
              value={lookupValue}
              onChange={(e) => setLookupValue(e.target.value)}
              required
            />
            <Input
              placeholder="Reason (optional)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <Button loading={lookupMutation.isPending} type="submit">
              Lookup
            </Button>
          </Card>

          {account && (
            <Card className="space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-text-primary">{account.label}</p>
                  <p className="font-mono text-xs text-text-secondary">{account.accountNumber}</p>
                  <p className="mt-1 text-sm text-text-primary">
                    Available:{' '}
                    <span className="font-bold">
                      {account.currency} {Number(account.balance).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </span>
                  </p>
                  <p className="text-xs text-text-secondary">
                    Ledger: {account.currency} {Number(account.ledgerBalance ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })} ·
                    Blocked: {account.currency} {Number(account.blockedAmount ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </p>
                </div>
                <Badge variant={account.status === 'ACTIVE' ? 'success' : 'danger'}>
                  {account.status}
                </Badge>
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                {canFreeze && !isFrozen && !isBlocked && !isClosed && (
                  <Button type="button" onClick={() => setPendingAction('freeze')} variant="secondary" title="Freeze this account temporarily">
                    Freeze
                  </Button>
                )}
                {canUnfreeze && isFrozen && (
                  <Button type="button" onClick={() => setPendingAction('unfreeze')} variant="secondary" title="Restore account access">
                    Unfreeze
                  </Button>
                )}
                {canBlock && isBlocked && (
                  <Button type="button" onClick={() => setPendingAction('unblock')} variant="secondary" title="Restore account access after a block">
                    Unblock
                  </Button>
                )}
                {canBlock && !isBlocked && !isClosed && (
                  <Button type="button" onClick={() => setPendingAction('block')} variant="danger" title="Permanently block this account">
                    Block
                  </Button>
                )}
                {canBlock && !isBlocked && !isClosed && (
                  <Button type="button" onClick={() => setPendingAction('close')} variant="danger" title="Close this account after funds reconciliation">
                    Close Account
                  </Button>
                )}
              </div>
              {account && !canAnyRestriction && !isClosed && (
                <StatusNoticeCard
                  title="View-only access"
                  message="Restriction actions require an administrator."
                  variant="info"
                />
              )}
              {isClosed && (
                <StatusNoticeCard
                  title="Account actions locked"
                  message="This account is closed. Further restriction actions are unavailable."
                  variant="info"
                />
              )}
            </Card>
          )}
        </div>

        <div className="space-y-4">
          {!account ? (
            <StatusNoticeCard
              title="Customer snapshot"
              message="Lookup an account to view customer details, balances breakdown, and KYC information."
              variant="info"
            />
          ) : (
            <Card className="space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-text-primary">{account.owner?.name ?? 'Customer'}</p>
                  <p className="text-xs text-text-tertiary">{account.owner?.phoneNumber ?? '—'}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-text-tertiary">KYC</p>
                  <p className="text-sm font-semibold text-text-primary">{account.owner?.kycStatus ?? '—'}</p>
                </div>
              </div>

              {canReviewKyc && ownerId ? (
                <Link to={ROUTE_PATHS.staffTellerCustomerProfile(ownerId)}>
                  <Button type="button" variant="secondary" className="w-full sm:w-auto">
                    Edit customer KYC
                  </Button>
                </Link>
              ) : null}

              {customerQuery.isLoading ? (
                <p className="text-sm text-text-secondary">Loading KYC profile…</p>
              ) : customerQuery.isError ? (
                <StatusNoticeCard
                  title="KYC data unavailable"
                  message="Unable to load KYC profile/documents for this customer."
                  variant="warning"
                />
              ) : (
                <>
                  <div>
                    <p className="text-sm font-semibold text-text-primary">KYC completeness</p>
                    <p className="mt-1 text-xs text-text-tertiary">
                      {customerQuery.data?.kyc?.completeness?.is_valid ? 'Complete' : 'Incomplete'} · Missing fields:{' '}
                      {(customerQuery.data?.kyc?.completeness?.missing_fields ?? []).join(', ') || '—'} · Missing docs:{' '}
                      {(customerQuery.data?.kyc?.completeness?.missing_documents ?? []).join(', ') || '—'}
                    </p>
                  </div>

                  <div>
                    <p className="text-sm font-semibold text-text-primary">KYC profile</p>
                    {customerQuery.data?.kyc?.profile ? (
                      <div className="mt-2 grid gap-2 sm:grid-cols-2">
                        <div>
                          <p className="text-[11px] text-text-tertiary">Legal name</p>
                          <p className="text-sm text-text-primary">{String((customerQuery.data.kyc.profile as any).legal_full_name ?? '—')}</p>
                        </div>
                        <div>
                          <p className="text-[11px] text-text-tertiary">DOB</p>
                          <p className="text-sm text-text-primary">{String((customerQuery.data.kyc.profile as any).date_of_birth ?? '—')}</p>
                        </div>
                        <div>
                          <p className="text-[11px] text-text-tertiary">Nationality</p>
                          <p className="text-sm text-text-primary">{String((customerQuery.data.kyc.profile as any).nationality ?? '—')}</p>
                        </div>
                        <div>
                          <p className="text-[11px] text-text-tertiary">ID</p>
                          <p className="text-sm text-text-primary">
                            {String((customerQuery.data.kyc.profile as any).id_type ?? '—')} · {String((customerQuery.data.kyc.profile as any).id_number ?? '—')}
                          </p>
                        </div>
                        <div className="sm:col-span-2">
                          <p className="text-[11px] text-text-tertiary">Address</p>
                          <p className="text-sm text-text-primary">
                            {String((customerQuery.data.kyc.profile as any).address_line1 ?? '—')},{' '}
                            {String((customerQuery.data.kyc.profile as any).address_city ?? '—')},{' '}
                            {String((customerQuery.data.kyc.profile as any).address_country ?? '—')}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <p className="mt-1 text-sm text-text-secondary">No KYC profile submitted yet.</p>
                    )}
                  </div>

                  <div>
                    <p className="text-sm font-semibold text-text-primary">KYC documents</p>
                    {customerQuery.data?.kyc?.documents?.length ? (
                      <div className="mt-2 space-y-2">
                        {customerQuery.data.kyc.documents.map((d: any) => (
                          <div key={String(d.id ?? d.file)} className="flex items-center justify-between gap-2 rounded-lg border border-border px-3 py-2">
                            <div>
                              <p className="text-xs font-semibold text-text-primary">{String(d.document_type ?? '').replace(/_/g, ' ')}</p>
                              <p className="text-[11px] text-text-tertiary">{String(d.status ?? '')}</p>
                            </div>
                            {d.file ? (
                              <a
                                href={String(d.file)}
                                target="_blank"
                                rel="noreferrer"
                                className="rounded-lg border border-border bg-surface-secondary px-2.5 py-1 text-xs font-semibold text-text-primary hover:bg-surface-tertiary"
                              >
                                View
                              </a>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-1 text-sm text-text-secondary">No documents uploaded yet.</p>
                    )}
                  </div>
                </>
              )}
            </Card>
          )}
        </div>
      </div>

      {pendingAction && (
        <ConfirmationModal
          title={
            pendingAction === 'freeze'   ? 'Freeze account'   :
            pendingAction === 'unfreeze' ? 'Unfreeze account' :
            pendingAction === 'block'    ? 'Block account'    :
            pendingAction === 'unblock'  ? 'Unblock account'  :
            'Close account'
          }
          description={
            pendingAction === 'freeze'   ? 'The account holder will not be able to make transactions while frozen.' :
            pendingAction === 'unfreeze' ? 'Restore full access to this account.' :
            pendingAction === 'block'    ? 'Permanently block this account. This action is hard to reverse.' :
            pendingAction === 'unblock'  ? 'Restore full access to this account after it was blocked.' :
            'Permanently close this account. All funds should be withdrawn first.'
          }
          confirmLabel={
            pendingAction === 'unfreeze' ? 'Unfreeze' :
            pendingAction === 'freeze'   ? 'Freeze' :
            pendingAction === 'block'    ? 'Block' :
            pendingAction === 'unblock'  ? 'Unblock' :
            'Close'
          }
          variant={
            pendingAction === 'freeze' || pendingAction === 'unfreeze' || pendingAction === 'unblock'
              ? 'warning'
              : 'danger'
          }
          loading={false}
          onConfirm={() => execAction(pendingAction)}
          onCancel={() => setPendingAction(null)}
        />
      )}
    </div>
  )
}
