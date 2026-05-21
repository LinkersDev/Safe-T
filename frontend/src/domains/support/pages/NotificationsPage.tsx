import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import {
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../services/support-service'

export function NotificationsPage() {
  const queryClient = useQueryClient()
  const [unreadOnly, setUnreadOnly] = useState(false)

  const notificationsQuery = useQuery({
    queryKey: ['notifications', unreadOnly],
    queryFn: () => getNotifications(unreadOnly),
  })

  const readOneMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['notifications'] }),
        queryClient.invalidateQueries({ queryKey: ['notification-count'] }),
      ])
    },
  })

  const readAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['notifications'] }),
        queryClient.invalidateQueries({ queryKey: ['notification-count'] }),
      ])
    },
  })

  return (
    <div className="max-w-2xl space-y-4">
        <div className="grid gap-2 sm:grid-cols-2">
          <Button
            onClick={() => setUnreadOnly((current) => !current)}
            type="button"
            variant="secondary"
          >
            {unreadOnly ? 'Show all' : 'Unread only'}
          </Button>
          <Button loading={readAllMutation.isPending} onClick={() => readAllMutation.mutate()} type="button">
            Mark all read
          </Button>
        </div>

        {notificationsQuery.isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : (
          <div className="space-y-3">
            {notificationsQuery.data?.map((notification) => (
              <Card key={notification.id} className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-semibold text-text-primary">{notification.title}</span>
                  {!notification.isRead ? <Badge variant="info">Unread</Badge> : null}
                </div>
                <p className="text-sm text-text-secondary">{notification.message}</p>
                <div className="flex items-center justify-between">
                  <p className="text-xs text-text-tertiary">
                    {new Date(notification.createdAt).toLocaleString()}
                  </p>
                  {!notification.isRead ? (
                    <button
                      className="text-sm font-semibold text-brand-info"
                      disabled={readOneMutation.isPending}
                      onClick={() => readOneMutation.mutate(notification.id)}
                      type="button"
                    >
                      Mark read
                    </button>
                  ) : null}
                </div>
              </Card>
            ))}
          </div>
        )}
    </div>
  )
}
