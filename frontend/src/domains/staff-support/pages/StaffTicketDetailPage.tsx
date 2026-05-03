import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { useToast } from '../../../shared/components/ui/Toast'
import {
  getStaffTicketDetail,
  replyStaffTicket,
  assignStaffTicket,
  resolveStaffTicket,
} from '../../staff/services/staff-service'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { cn } from '../../../core/utils/cn'

export function StaffTicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const toast = useToast()
  const [replyBody, setReplyBody] = useState('')
  const [replyInternal, setReplyInternal] = useState(false)

  const ticketQuery = useQuery({
    queryKey: ['staff-ticket-detail', ticketId],
    queryFn: () => getStaffTicketDetail(ticketId!),
    enabled: Boolean(ticketId),
  })

  const invalidate = () => qc.invalidateQueries({ queryKey: ['staff-ticket-detail', ticketId] })

  const replyMutation = useMutation({
    mutationFn: (body: string) => replyStaffTicket(ticketId!, body, { isInternal: replyInternal }),
    onSuccess: () => {
      invalidate()
      setReplyBody('')
      setReplyInternal(false)
      toast.success('Reply sent.')
    },
    onError: () => toast.error('Failed to send reply.'),
  })

  const assignMutation = useMutation({
    mutationFn: () => assignStaffTicket(Number(ticketId)),
    onSuccess: () => { invalidate(); toast.success('Ticket assigned to you.') },
    onError: () => toast.error('Failed to assign ticket.'),
  })

  const resolveMutation = useMutation({
    mutationFn: () => resolveStaffTicket(Number(ticketId)),
    onSuccess: () => { invalidate(); toast.success('Ticket resolved.') },
    onError: () => toast.error('Failed to resolve ticket.'),
  })

  if (ticketQuery.isLoading) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <Skeleton className="h-8 w-40 rounded-lg" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    )
  }

  if (!ticketQuery.data) {
    return (
      <div className="mx-auto max-w-2xl py-16 text-center">
        <p className="text-text-secondary">Ticket not found.</p>
        <button
          onClick={() => navigate(ROUTE_PATHS.staffSupport)}
          className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors"
        >
          Back to support queue
        </button>
      </div>
    )
  }

  const ticket = ticketQuery.data
  const statusVariant =
    ticket.status === 'CLOSED' ? 'info' :
    ticket.status === 'RESOLVED' ? 'success' :
    ticket.status === 'IN_PROGRESS' ? 'warning' : 'info'

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <button
        onClick={() => navigate(ROUTE_PATHS.staffSupport)}
        className="flex items-center gap-1.5 text-sm font-medium text-emerald-600 hover:text-emerald-700 transition-colors"
      >
        ← Back to support queue
      </button>

      {/* Ticket header */}
      <div className="rounded-2xl border border-border bg-surface-primary p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-text-primary">{ticket.subject}</h2>
            <p className="text-sm text-text-secondary">{ticket.category.replace(/_/g, ' ')}</p>
          </div>
          <Badge variant={statusVariant}>{ticket.status.replace(/_/g, ' ')}</Badge>
        </div>
        {(ticket.customerName || ticket.customerPhoneNumber || ticket.customerId) && (
          <div className="mt-3 rounded-xl border border-border bg-surface-secondary px-4 py-3 text-sm">
            <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Customer</p>
            <div className="mt-1 space-y-0.5">
              <p className="font-semibold text-text-primary">{ticket.customerName ?? '—'}</p>
              <p className="text-sm text-text-secondary">{ticket.customerPhoneNumber ?? '—'}</p>
              <p className="text-xs text-text-tertiary">ID: {ticket.customerId ?? '—'}</p>
            </div>
          </div>
        )}
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-text-tertiary">
          <span>Assigned to: <span className="font-medium">{ticket.assignedToName ?? 'Unassigned'}</span></span>
          <span>Updated: {new Date(ticket.updatedAt).toLocaleString()}</span>
          <span>Created: {new Date(ticket.createdAt).toLocaleString()}</span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {!ticket.assignedToName && ticket.status !== 'CLOSED' && ticket.status !== 'RESOLVED' && (
            <Button
              className="!min-h-0 px-3 py-1.5 text-xs"
              onClick={() => assignMutation.mutate()}
              disabled={assignMutation.isPending}
              variant="secondary"
            >
              Assign to me
            </Button>
          )}
          {ticket.status !== 'RESOLVED' && ticket.status !== 'CLOSED' && (
            <Button
              className="!min-h-0 px-3 py-1.5 text-xs"
              onClick={() => resolveMutation.mutate()}
              disabled={resolveMutation.isPending}
            >
              Resolve ticket
            </Button>
          )}
        </div>
      </div>

      {/* Message thread */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
          Conversation ({ticket.messages.length})
        </h3>
        {ticket.messages.length === 0 ? (
          <p className="rounded-xl border border-border bg-surface-primary p-5 text-center text-sm text-text-secondary">
            No messages yet.
          </p>
        ) : (
          ticket.messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                'rounded-xl border border-border p-4',
                msg.isInternal ? 'bg-amber-50 border-amber-200' : 'bg-surface-primary',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-text-primary">
                  {msg.senderName ?? 'System'}
                  {msg.isInternal && (
                    <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                      Internal
                    </span>
                  )}
                </p>
                <span className="text-xs text-text-tertiary">
                  {new Date(msg.createdAt).toLocaleString()}
                </span>
              </div>
              <p className="mt-2 text-sm text-text-primary whitespace-pre-wrap">{msg.body}</p>
            </div>
          ))
        )}
      </div>

      {/* Reply box */}
      {ticket.status !== 'CLOSED' && (
        <div className="rounded-2xl border border-border bg-surface-primary p-5 space-y-3">
          <h3 className="text-sm font-semibold text-text-primary">Reply</h3>
          <label className="flex items-center gap-2 text-xs text-text-secondary">
            <input
              type="checkbox"
              checked={replyInternal}
              onChange={(e) => setReplyInternal(e.target.checked)}
            />
            Internal note (visible to staff only)
          </label>
          <textarea
            rows={4}
            value={replyBody}
            onChange={(e) => setReplyBody(e.target.value)}
            placeholder="Type your reply here…"
            className="w-full resize-none rounded-lg border border-border bg-surface-secondary px-3 py-2 text-sm text-text-primary outline-none focus:border-emerald-500"
          />
          <div className="flex justify-end">
            <Button
              onClick={() => replyMutation.mutate(replyBody)}
              disabled={!replyBody.trim() || replyMutation.isPending}
              loading={replyMutation.isPending}
            >
              Send reply
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
