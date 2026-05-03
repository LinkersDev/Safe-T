import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
import { DataTable, type Column } from '../../../shared/components/ui/DataTable'
import { Input } from '../../../shared/components/ui/Input'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { ConfirmationModal } from '../../../shared/components/ui/ConfirmationModal'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import { approveUser, getAllUsers, getPendingUsers, rejectUser, unlockUser } from '../../staff/services/staff-service'
import type { StaffUser } from '../../staff/types'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { useAuthSession } from '../../security/hooks/useAuthSession'

export function StaffUsersPage() {
  const { permissions } = useAuthSession()
  const canUnlockLogin = permissions.includes('unlock_user')
  const queryClient = useQueryClient()
  const toast = useToast()
  const [rejectTarget, setRejectTarget] = useState<StaffUser | null>(null)
  const [mode, setMode] = useState<'all' | 'pending'>('all')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setSearch(searchInput.trim())
    }, 300)
    return () => window.clearTimeout(handle)
  }, [searchInput])

  const usersQuery = useQuery({
    queryKey: ['staff-users', mode, search],
    queryFn: () => (mode === 'pending' ? getPendingUsers() : getAllUsers({ search, limit: 1000 })),
    placeholderData: (prev) => prev,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['staff-users'] })

  const usersCountLabel = useMemo(() => {
    const count = usersQuery.data?.length ?? 0
    return mode === 'pending' ? `${count} users in queue` : `${count} users`
  }, [mode, usersQuery.data?.length])

  const approveMutation = useMutation({
    mutationFn: approveUser,
    onSuccess: () => { invalidate(); toast.success('User approved.') },
    onError: () => toast.error('Failed to approve user.'),
  })

  const rejectMutation = useMutation({
    mutationFn: (userId: number) => rejectUser(userId, 'Rejected by staff review.'),
    onSuccess: () => { invalidate(); setRejectTarget(null); toast.success('User rejected.') },
    onError: () => toast.error('Failed to reject user.'),
  })

  const unlockMutation = useMutation({
    mutationFn: unlockUser,
    onSuccess: () => { invalidate(); toast.success('User unlocked.') },
    onError: () => toast.error('Failed to unlock user.'),
  })

  const columns: Column<StaffUser>[] = [
    {
      key: 'name',
      header: 'User',
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
        <div className="flex flex-col gap-1">
          <Badge
            variant={
              u.status === 'PENDING' ? 'warning' :
              u.status === 'BLOCKED' ? 'danger' : 'info'
            }
          >
            {u.status}
          </Badge>
          {!u.isActive && u.status !== 'BLOCKED' ? (
            <span className="text-[10px] font-semibold uppercase tracking-wide text-amber-700">
              Login locked
            </span>
          ) : null}
        </div>
      ),
    },
    {
      key: 'kyc',
      header: 'KYC',
      render: (u) => (
        <span className="text-xs text-text-secondary">{u.kycStatus}</span>
      ),
    },
    {
      key: 'joined',
      header: 'Joined',
      render: (u) => (
        <span className="text-xs text-text-tertiary">
          {new Date(u.createdAt).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (u) => (
        <div className="flex flex-wrap items-center gap-2">
          {u.status === 'PENDING' && (
            <>
              <Button
                className="!min-h-0 px-3 py-1.5 text-xs"
                onClick={(e) => { e.stopPropagation(); approveMutation.mutate(u.id) }}
                disabled={approveMutation.isPending}
              >
                Approve
              </Button>
              <Button
                className="!min-h-0 px-3 py-1.5 text-xs"
                onClick={(e) => { e.stopPropagation(); setRejectTarget(u) }}
                variant="danger"
                disabled={rejectMutation.isPending}
              >
                Reject
              </Button>
            </>
          )}
          {canUnlockLogin && !u.isActive && u.status !== 'BLOCKED' && (
            <Button
              className="!min-h-0 px-3 py-1.5 text-xs"
              onClick={(e) => {
                e.stopPropagation()
                unlockMutation.mutate(u.id)
              }}
              disabled={unlockMutation.isPending}
              variant="secondary"
              title="Clears failed-login lock (restores sign-in)."
            >
              Unlock login
            </Button>
          )}
        </div>
      ),
    },
  ]

  if (usersQuery.isError) {
    return (
      <StatusNoticeCard
        title="Users unavailable"
        message="User queue could not be loaded. Check connectivity or permissions."
        variant="error"
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-text-tertiary">{usersCountLabel}</p>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2">
            <Button
              className="!min-h-0 px-3 py-1.5 text-xs"
              variant={mode === 'all' ? 'primary' : 'secondary'}
              onClick={() => setMode('all')}
              type="button"
            >
              All users
            </Button>
            <Button
              className="!min-h-0 px-3 py-1.5 text-xs"
              variant={mode === 'pending' ? 'primary' : 'secondary'}
              onClick={() => setMode('pending')}
              type="button"
            >
              Pending queue
            </Button>
          </div>
          <Link
            to={ROUTE_PATHS.staffRegisterStaff}
            className="inline-flex min-h-[44px] items-center justify-center rounded-md bg-surface-secondary px-4 py-2 text-sm font-semibold text-text-primary transition-colors hover:bg-[#E6EBF2]"
          >
            Register staff
          </Link>
          <Input
            id="staff-user-search"
            placeholder="Search name or phone…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </div>
      </div>
      {usersQuery.isPending && !usersQuery.data ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : (
        <DataTable
          columns={columns}
          rows={usersQuery.data ?? []}
          keyExtractor={(u) => u.id}
          emptyMessage={mode === 'pending' ? 'No pending users — all caught up!' : 'No users found.'}
        />
      )}

      {rejectTarget && (
        <ConfirmationModal
          title="Reject user"
          description={`Reject "${rejectTarget.fullName}" (${rejectTarget.phoneNumber})? This will prevent them from accessing the system.`}
          confirmLabel="Reject"
          variant="danger"
          loading={rejectMutation.isPending}
          onConfirm={() => rejectMutation.mutate(rejectTarget.id)}
          onCancel={() => setRejectTarget(null)}
        />
      )}
    </div>
  )
}
