import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { normalizeApiError } from '../../../core/api/error-normalizer'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import { Input } from '../../../shared/components/ui/Input'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { createTicket, getTickets } from '../services/support-service'
import type { TicketCategory, TicketStatus } from '../types'

const categories: TicketCategory[] = [
  'GENERAL',
  'ACCOUNT_ISSUE',
  'PAYMENT_ISSUE',
  'KYC_ISSUE',
  'CARD_ISSUE',
  'OTHER',
]

function statusVariant(status: TicketStatus) {
  if (status === 'CLOSED') return 'danger'
  if (status === 'RESOLVED') return 'success'
  if (status === 'IN_PROGRESS') return 'warning'
  return 'info'
}

export function TicketsPage() {
  const queryClient = useQueryClient()
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [category, setCategory] = useState<TicketCategory>('GENERAL')
  const [error, setError] = useState<string | null>(null)

  const ticketsQuery = useQuery({ queryKey: ['support-tickets'], queryFn: getTickets })
  const createMutation = useMutation({
    mutationFn: createTicket,
    onSuccess: async () => {
      setSubject('')
      setBody('')
      setCategory('GENERAL')
      setError(null)
      await queryClient.invalidateQueries({ queryKey: ['support-tickets'] })
    },
    onError: (nextError) => setError(normalizeApiError(nextError).detail),
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    createMutation.mutate({ subject, body, category })
  }

  return (
    <div className="max-w-2xl space-y-4">
        <Card as="form" className="space-y-4" onSubmit={handleSubmit}>
          <Input
            placeholder="Subject"
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            required
          />
          <select
            className="min-h-[44px] w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none"
            value={category}
            onChange={(event) => setCategory(event.target.value as TicketCategory)}
          >
            {categories.map((item) => (
              <option key={item} value={item}>
                {item.replaceAll('_', ' ')}
              </option>
            ))}
          </select>
          <textarea
            className="min-h-24 w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none"
            placeholder="How can we help?"
            value={body}
            onChange={(event) => setBody(event.target.value)}
            required
          />
          {error ? <p className="text-sm text-brand-danger">{error}</p> : null}
          <Button className="w-full" loading={createMutation.isPending} type="submit">
            Create ticket
          </Button>
        </Card>

        {ticketsQuery.isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : (
          <div className="space-y-3">
            {ticketsQuery.data?.map((ticket) => (
              <Link key={ticket.id} to={ROUTE_PATHS.ticketDetail(ticket.id)}>
                <Card className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-text-primary">{ticket.subject}</span>
                    <Badge variant={statusVariant(ticket.status)}>{ticket.status.replace('_', ' ')}</Badge>
                  </div>
                  <p className="text-xs text-text-tertiary">{ticket.category.replaceAll('_', ' ')}</p>
                </Card>
              </Link>
            ))}
          </div>
        )}
    </div>
  )
}
