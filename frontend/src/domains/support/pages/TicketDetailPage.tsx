import { useState, type FormEvent } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { normalizeApiError } from '../../../core/api/error-normalizer'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { closeTicket, getTicketDetail, replyToTicket } from '../services/support-service'

export function TicketDetailPage() {
  const queryClient = useQueryClient()
  const params = useParams()
  const ticketId = Number(params.ticketId)
  const [body, setBody] = useState('')
  const [error, setError] = useState<string | null>(null)

  const ticketQuery = useQuery({
    queryKey: ['support-ticket', ticketId],
    queryFn: () => getTicketDetail(ticketId),
    enabled: Number.isFinite(ticketId),
  })

  const replyMutation = useMutation({
    mutationFn: () => replyToTicket(ticketId, body),
    onSuccess: async () => {
      setBody('')
      setError(null)
      await queryClient.invalidateQueries({ queryKey: ['support-ticket', ticketId] })
    },
    onError: (nextError) => setError(normalizeApiError(nextError).detail),
  })

  const closeMutation = useMutation({
    mutationFn: () => closeTicket(ticketId),
    onSuccess: async () => {
      setError(null)
      await queryClient.invalidateQueries({ queryKey: ['support-ticket', ticketId] })
      await queryClient.invalidateQueries({ queryKey: ['support-tickets'] })
    },
    onError: (nextError) => setError(normalizeApiError(nextError).detail),
  })

  if (!Number.isFinite(ticketId)) {
    return <Navigate to={ROUTE_PATHS.tickets} replace />
  }

  const ticket = ticketQuery.data
  const canReply = ticket?.status === 'OPEN' || ticket?.status === 'IN_PROGRESS'

  function handleReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (canReply) replyMutation.mutate()
  }

  return (
    <div className="max-w-2xl">
      {ticketQuery.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : ticket ? (
        <div className="space-y-4">
          <Card className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-text-primary">{ticket.subject}</span>
              <Badge variant={canReply ? 'info' : ticket.status === 'RESOLVED' ? 'success' : 'danger'}>
                {ticket.status.replace('_', ' ')}
              </Badge>
            </div>
            <p className="text-xs text-text-tertiary">{ticket.category.replaceAll('_', ' ')}</p>
          </Card>

          <div className="space-y-3">
            {ticket.messages.map((message) => (
              <Card key={message.id} className="space-y-1 shadow-none">
                <p className="text-sm text-text-secondary">{message.senderName ?? 'Support'}</p>
                <p className="text-sm text-text-primary">{message.body}</p>
                <p className="text-xs text-text-tertiary">
                  {new Date(message.createdAt).toLocaleString()}
                </p>
              </Card>
            ))}
          </div>

          <Card as="form" className="space-y-3" onSubmit={handleReply}>
            <textarea
              className="min-h-24 w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none disabled:opacity-60"
              disabled={!canReply}
              placeholder={canReply ? 'Write a reply' : 'Replies are disabled for closed/resolved tickets'}
              value={body}
              onChange={(event) => setBody(event.target.value)}
              required
            />
            {error ? <p className="text-sm text-brand-danger">{error}</p> : null}
            <div className="grid gap-2 sm:grid-cols-2">
              <Button disabled={!canReply} loading={replyMutation.isPending} type="submit">
                Reply
              </Button>
              <Button
                disabled={ticket.status === 'CLOSED'}
                loading={closeMutation.isPending}
                onClick={() => closeMutation.mutate()}
                type="button"
                variant="secondary"
              >
                Close ticket
              </Button>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  )
}
