import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Search, CreditCard, User, ShieldCheck, FileText, ArrowUpRight } from 'lucide-react'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
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

const cardBase = 'card-hover rounded-xl border border-[#E2E8F0] bg-white p-5 relative overflow-hidden'
const cardShadow = { boxShadow: '0 4px 20px rgba(10, 37, 64, 0.08)', transition: 'all 0.2s ease' }
const inputOverride = 'border border-[#E2E8F0] bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 hover:border-slate-300'

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
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          {/* Lookup */}
          <div className={`${cardBase} border-l-[3px] border-l-blue-500`} style={cardShadow}>
            <div className="flex items-center gap-2 mb-4">
              <Search size={18} strokeWidth={2} className="text-blue-600" />
              <p className="text-sm font-semibold text-slate-900">Account Lookup</p>
            </div>
            <form onSubmit={handleLookup} className="space-y-3">
              <Input
                inputMode="tel"
                placeholder="Phone (+E.164), account number, or account id"
                value={lookupValue}
                onChange={(e) => setLookupValue(e.target.value)}
                required
                className={inputOverride}
              />
              <Input
                placeholder="Reason (optional)"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className={inputOverride}
              />
              <Button loading={lookupMutation.isPending} type="submit">
                Lookup
              </Button>
            </form>
          </div>

          {/* Account details */}
          {account && (
            <div className={`${cardBase} border-l-[3px] border-l-blue-500`} style={cardShadow}>
              <div className="flex items-start justify-between gap-3 mb-5">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                    <CreditCard size={20} strokeWidth={2} />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-900">{account.label}</p>
                    <p className="font-mono text-xs text-slate-500 mt-0.5">{account.accountNumber}</p>
                    <p className="mt-2 text-sm text-slate-700 leading-relaxed">
                      Available:{' '}
                      <span className="font-bold text-slate-900">
                        {account.currency} {Number(account.balance).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </span>
                    </p>
                    <p className="text-xs text-slate-500 leading-relaxed">
                      Ledger: {account.currency} {Number(account.ledgerBalance ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })} ·
                      Blocked: {account.currency} {Number(account.blockedAmount ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </p>
                  </div>
                </div>
                <Badge variant={account.status === 'ACTIVE' ? 'success' : 'danger'}>
                  {account.status}
                </Badge>
              </div>

              {/* Action buttons with visual hierarchy */}
              <div className="space-y-3">
                <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Account Actions</p>
                <div className="flex flex-wrap gap-2">
                  {canFreeze && !isFrozen && !isBlocked && !isClosed && (
                    <button
                      type="button"
                      onClick={() => setPendingAction('freeze')}
                      title="Freeze this account temporarily"
                      className="rounded-lg border border-[#0A2540] bg-white px-4 py-2 text-sm font-semibold text-[#0A2540] hover:bg-slate-50 transition-all"
                    >
                      Freeze
                    </button>
                  )}
                  {canUnfreeze && isFrozen && (
                    <button
                      type="button"
                      onClick={() => setPendingAction('unfreeze')}
                      title="Restore account access"
                      className="rounded-lg border border-[#0A2540] bg-white px-4 py-2 text-sm font-semibold text-[#0A2540] hover:bg-slate-50 transition-all"
                    >
                      Unfreeze
                    </button>
                  )}
                  {canBlock && isBlocked && (
                    <button
                      type="button"
                      onClick={() => setPendingAction('unblock')}
                      title="Restore account access after a block"
                      className="rounded-lg border border-[#0A2540] bg-white px-4 py-2 text-sm font-semibold text-[#0A2540] hover:bg-slate-50 transition-all"
                    >
                      Unblock
                    </button>
                  )}
                  {canBlock && !isBlocked && !isClosed && (
                    <button
                      type="button"
                      onClick={() => setPendingAction('block')}
                      title="Permanently block this account"
                      className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600 shadow-sm hover:shadow-md transition-all"
                    >
                      Block
                    </button>
                  )}
                  {canBlock && !isBlocked && !isClosed && (
                    <button
                      type="button"
                      onClick={() => setPendingAction('close')}
                      title="Close this account after funds reconciliation"
                      className="rounded-lg bg-rose-500 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-600 shadow-sm hover:shadow-md transition-all"
                    >
                      Close Account
                    </button>
                  )}
                </div>
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
            </div>
          )}
        </div>

        {/* Customer / KYC */}
        <div className="space-y-6">
          {!account ? (
            <StatusNoticeCard
              title="Customer snapshot"
              message="Lookup an account to view customer details, balances breakdown, and KYC information."
              variant="info"
            />
          ) : (
            <div className={`${cardBase} border-l-[3px] border-l-emerald-500`} style={cardShadow}>
              {/* Customer header */}
              <div className="flex items-start justify-between gap-3 mb-5">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                    <User size={20} strokeWidth={2} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{account.owner?.name ?? 'Customer'}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{account.owner?.phoneNumber ?? '—'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <ShieldCheck size={14} strokeWidth={2} className="text-emerald-600" />
                  <span className="text-xs font-semibold text-emerald-600">{account.owner?.kycStatus ?? '—'}</span>
                </div>
              </div>

              {canReviewKyc && ownerId ? (
                <Link
                  to={ROUTE_PATHS.staffTellerCustomerProfile(ownerId)}
                  className="inline-flex items-center gap-2 rounded-lg border border-[#0A2540] bg-white px-4 py-2 text-sm font-semibold text-[#0A2540] hover:bg-slate-50 transition-all mb-5"
                >
                  <ArrowUpRight size={16} strokeWidth={2} />
                  Edit customer KYC
                </Link>
              ) : null}

              {customerQuery.isLoading ? (
                <p className="text-sm text-slate-500">Loading KYC profile…</p>
              ) : customerQuery.isError ? (
                <StatusNoticeCard
                  title="KYC data unavailable"
                  message="Unable to load KYC profile/documents for this customer."
                  variant="warning"
                />
              ) : (
                <div className="space-y-6">
                  {/* KYC completeness */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <ShieldCheck size={16} strokeWidth={2} className="text-slate-500" />
                        <p className="text-sm font-semibold text-slate-900">KYC Completeness</p>
                      </div>
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          customerQuery.data?.kyc?.completeness?.is_valid
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-amber-100 text-amber-700'
                        }`}
                      >
                        {customerQuery.data?.kyc?.completeness?.is_valid ? 'Approved' : 'Incomplete'}
                      </span>
                    </div>

                    {/* Missing fields as readable list */}
                    {!customerQuery.data?.kyc?.completeness?.is_valid && (
                      <div className="space-y-2">
                        {(() => {
                          const missingFields = customerQuery.data?.kyc?.completeness?.missing_fields ?? []
                          const missingDocs = customerQuery.data?.kyc?.completeness?.missing_documents ?? []
                          return (
                            <>
                              {missingFields.length > 0 && (
                                <div className="rounded-lg bg-amber-50 border border-amber-200 p-3">
                                  <p className="text-xs font-semibold text-amber-700 mb-1.5">Missing Fields</p>
                                  <ul className="space-y-1">
                                    {missingFields.map((field, i) => (
                                      <li key={i} className="text-xs text-amber-700 flex items-center gap-1.5">
                                        <span className="h-1 w-1 rounded-full bg-amber-500" />
                                        {String(field).replace(/_/g, ' ')}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {missingDocs.length > 0 && (
                                <div className="rounded-lg bg-amber-50 border border-amber-200 p-3">
                                  <p className="text-xs font-semibold text-amber-700 mb-1.5">Missing Documents</p>
                                  <ul className="space-y-1">
                                    {missingDocs.map((doc, i) => (
                                      <li key={i} className="text-xs text-amber-700 flex items-center gap-1.5">
                                        <span className="h-1 w-1 rounded-full bg-amber-500" />
                                        {String(doc).replace(/_/g, ' ')}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {missingFields.length === 0 && missingDocs.length === 0 && (
                                <p className="text-xs text-slate-500">All fields and documents are present, but KYC is not yet approved.</p>
                              )}
                            </>
                          )
                        })()}
                      </div>
                    )}
                    {customerQuery.data?.kyc?.completeness?.is_valid && (
                      <p className="text-xs text-slate-500">All KYC fields and documents are complete.</p>
                    )}
                  </div>

                  {/* KYC profile */}
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <User size={16} strokeWidth={2} className="text-slate-500" />
                      <p className="text-sm font-semibold text-slate-900">KYC Profile</p>
                    </div>
                    {customerQuery.data?.kyc?.profile ? (
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-lg bg-slate-50 p-3">
                          <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Legal name</p>
                          <p className="text-sm text-slate-900 mt-1">{String((customerQuery.data.kyc.profile as any).legal_full_name ?? '—')}</p>
                        </div>
                        <div className="rounded-lg bg-slate-50 p-3">
                          <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">DOB</p>
                          <p className="text-sm text-slate-900 mt-1">{String((customerQuery.data.kyc.profile as any).date_of_birth ?? '—')}</p>
                        </div>
                        <div className="rounded-lg bg-slate-50 p-3">
                          <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Nationality</p>
                          <p className="text-sm text-slate-900 mt-1">{String((customerQuery.data.kyc.profile as any).nationality ?? '—')}</p>
                        </div>
                        <div className="rounded-lg bg-slate-50 p-3">
                          <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">ID</p>
                          <p className="text-sm text-slate-900 mt-1">
                            {String((customerQuery.data.kyc.profile as any).id_type ?? '—')} · {String((customerQuery.data.kyc.profile as any).id_number ?? '—')}
                          </p>
                        </div>
                        <div className="sm:col-span-2 rounded-lg bg-slate-50 p-3">
                          <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Address</p>
                          <p className="text-sm text-slate-900 mt-1">
                            {String((customerQuery.data.kyc.profile as any).address_line1 ?? '—')},{' '}
                            {String((customerQuery.data.kyc.profile as any).address_city ?? '—')},{' '}
                            {String((customerQuery.data.kyc.profile as any).address_country ?? '—')}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">No KYC profile submitted yet.</p>
                    )}
                  </div>

                  {/* KYC documents */}
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <FileText size={16} strokeWidth={2} className="text-slate-500" />
                      <p className="text-sm font-semibold text-slate-900">KYC Documents</p>
                    </div>
                    {customerQuery.data?.kyc?.documents?.length ? (
                      <div className="space-y-3">
                        {customerQuery.data.kyc.documents.map((d: any) => (
                          <div
                            key={String(d.id ?? d.file)}
                            className="flex items-center justify-between gap-2 rounded-xl border border-[#E2E8F0] bg-white px-4 py-3"
                            style={{ boxShadow: '0 2px 8px rgba(10, 37, 64, 0.04)' }}
                          >
                            <div>
                              <p className="text-xs font-semibold text-slate-900">{String(d.document_type ?? '').replace(/_/g, ' ')}</p>
                              <p className="text-[11px] text-slate-500 mt-0.5">{String(d.status ?? '')}</p>
                            </div>
                            {d.file ? (
                              <a
                                href={String(d.file)}
                                target="_blank"
                                rel="noreferrer"
                                className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-all"
                              >
                                View
                              </a>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">No documents uploaded yet.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
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
