import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
import { DataTable, type Column } from '../../../shared/components/ui/DataTable'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import {
  assignStaffTicket,
  getStaffSupportTickets,
  resolveStaffTicket,
} from '../../staff/services/staff-service'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import type { StaffSupportTicket } from '../../staff/types'

export function StaffSupportPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const toast = useToast()
  const [filter, setFilter] = useState<'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED' | 'UNASSIGNED' | 'ALL'>('OPEN')

  const ticketsQuery = useQuery({
    queryKey: ['staff-support-tickets', filter],
    queryFn: () =>
      getStaffSupportTickets(
        filter === 'ALL'
          ? undefined
          : filter === 'UNASSIGNED'
            ? { unassigned: true }
            : { status: filter },
      ),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['staff-support-tickets'] })

  const assignMutation = useMutation({
    mutationFn: assignStaffTicket,
    onSuccess: () => { invalidate(); toast.success('Ticket assigned to you.') },
    onError: () => toast.error('Failed to assign ticket.'),
  })
  const resolveMutation = useMutation({
    mutationFn: resolveStaffTicket,
    onSuccess: () => { invalidate(); toast.success('Ticket resolved.') },
    onError: () => toast.error('Failed to resolve ticket.'),
  })

  const columns: Column<StaffSupportTicket>[] = [
    {
      key: 'ticket',
      header: 'Ticket',
      render: (t) => (
        <div>
          <p className="font-semibold text-text-primary">{t.subject}</p>
          <p className="text-xs text-text-tertiary">{t.category.replaceAll('_', ' ')}</p>
        </div>
      ),
    },
    {
      key: 'assigned',
      header: 'Assigned To',
      render: (t) => (
        <span className="text-sm text-text-secondary">{t.assignedToName ?? 'Unassigned'}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (t) => (
        <Badge
          variant={
            t.status === 'CLOSED' ? 'info' :
            t.status === 'RESOLVED' ? 'success' :
            t.status === 'IN_PROGRESS' ? 'warning' : 'info'
          }
        >
          {t.status.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    {
      key: 'updated',
      header: 'Updated',
      render: (t) => (
        <span className="text-xs text-text-tertiary">
          {new Date(t.updatedAt).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (t) => (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            className="!min-h-0 px-3 py-1.5 text-xs"
            onClick={(e) => { e.stopPropagation(); navigate(ROUTE_PATHS.staffTicketDetail(t.id)) }}
            variant="secondary"
          >
            View
          </Button>
          {!t.assignedToName && (
            <Button
              className="!min-h-0 px-3 py-1.5 text-xs"
              onClick={(e) => { e.stopPropagation(); assignMutation.mutate(t.id) }}
              variant="secondary"
              disabled={assignMutation.isPending || t.status === 'CLOSED' || t.status === 'RESOLVED'}
            >
              Assign me
            </Button>
          )}
          {t.status !== 'CLOSED' && t.status !== 'RESOLVED' && (
            <Button
              className="!min-h-0 px-3 py-1.5 text-xs"
              disabled={resolveMutation.isPending}
              onClick={(e) => { e.stopPropagation(); resolveMutation.mutate(t.id) }}
            >
              Resolve
            </Button>
          )}
        </div>
      ),
    },
  ]

  if (ticketsQuery.isLoading) {
    return <Skeleton className="h-64 w-full rounded-xl" />
  }

  if (ticketsQuery.isError) {
    return (
      <StatusNoticeCard
        title="Support queue unavailable"
        message="Support tickets could not be loaded."
        variant="error"
      />
    )
  }

  const FilterButton = ({ value, label }: { value: typeof filter; label: string }) => (
    <button
      type="button"
      onClick={() => setFilter(value)}
      className={[
        'rounded-full px-3 py-1.5 text-xs font-semibold border transition-colors',
        filter === value
          ? 'bg-emerald-600 text-white border-emerald-600'
          : 'bg-surface-primary text-text-secondary border-border hover:bg-surface-secondary',
      ].join(' ')}
    >
      {label}
    </button>
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <FilterButton value="OPEN" label="Open" />
        <FilterButton value="UNASSIGNED" label="Unassigned" />
        <FilterButton value="IN_PROGRESS" label="In progress" />
        <FilterButton value="RESOLVED" label="Resolved" />
        <FilterButton value="CLOSED" label="Closed" />
        <FilterButton value="ALL" label="All" />
      </div>
      <p className="text-sm text-text-tertiary">
        {ticketsQuery.data?.filter((t) => t.status !== 'CLOSED' && t.status !== 'RESOLVED').length ?? 0} open tickets
      </p>
      <DataTable
        columns={columns}
        rows={ticketsQuery.data ?? []}
        keyExtractor={(t) => t.id}
        emptyMessage="No tickets in the queue."
        onRowClick={(t) => navigate(ROUTE_PATHS.staffTicketDetail(t.id))}
      />
    </div>
  )
}
