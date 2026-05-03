import { apiClient } from '../../../core/api/client'
import type {
  Notification,
  SupportTicket,
  SupportTicketDetail,
  SupportTicketMessage,
  TicketCategory,
} from '../types'

type BackendTicket = {
  id: number
  subject: string
  category: TicketCategory
  status: SupportTicket['status']
  assigned_to_name: string | null
  created_at: string
  updated_at: string
}

type BackendMessage = {
  id: number
  sender_name: string | null
  body: string
  is_internal: boolean
  created_at: string
}

type BackendTicketDetail = BackendTicket & {
  messages: BackendMessage[]
}

type BackendNotification = {
  id: number
  notification_type: string
  title: string
  message: string
  is_read: boolean
  reference_type: string
  reference_id: string
  created_at: string
}

function mapTicket(ticket: BackendTicket): SupportTicket {
  return {
    id: ticket.id,
    subject: ticket.subject,
    category: ticket.category,
    status: ticket.status,
    assignedToName: ticket.assigned_to_name,
    createdAt: ticket.created_at,
    updatedAt: ticket.updated_at,
  }
}

function mapMessage(message: BackendMessage): SupportTicketMessage {
  return {
    id: message.id,
    senderName: message.sender_name,
    body: message.body,
    isInternal: message.is_internal,
    createdAt: message.created_at,
  }
}

function mapTicketDetail(ticket: BackendTicketDetail): SupportTicketDetail {
  return {
    ...mapTicket(ticket),
    messages: ticket.messages.map(mapMessage),
  }
}

function mapNotification(notification: BackendNotification): Notification {
  return {
    id: notification.id,
    notificationType: notification.notification_type,
    title: notification.title,
    message: notification.message,
    isRead: notification.is_read,
    referenceType: notification.reference_type,
    referenceId: notification.reference_id,
    createdAt: notification.created_at,
  }
}

export async function getTickets() {
  const response = await apiClient.get<BackendTicket[]>('/api/support/tickets/')
  return response.data.map(mapTicket)
}

export async function createTicket(payload: {
  subject: string
  body: string
  category: TicketCategory
}) {
  const response = await apiClient.post<BackendTicket>('/api/support/tickets/', payload)
  return mapTicket(response.data)
}

export async function getTicketDetail(ticketId: number) {
  const response = await apiClient.get<BackendTicketDetail>(`/api/support/tickets/${ticketId}/`)
  return mapTicketDetail(response.data)
}

export async function replyToTicket(ticketId: number, body: string) {
  const response = await apiClient.post<BackendMessage>(`/api/support/tickets/${ticketId}/reply/`, {
    body,
  })
  return mapMessage(response.data)
}

export async function closeTicket(ticketId: number) {
  const response = await apiClient.post<{ detail: string; status: SupportTicket['status'] }>(
    `/api/support/tickets/${ticketId}/close/`,
  )
  return response.data
}

export async function getNotifications(unreadOnly = false) {
  const response = await apiClient.get<BackendNotification[]>('/api/support/notifications/', {
    params: unreadOnly ? { unread: '1' } : undefined,
  })
  return response.data.map(mapNotification)
}

export async function markNotificationRead(notificationId: number) {
  const response = await apiClient.post<BackendNotification>(
    `/api/support/notifications/${notificationId}/read/`,
  )
  return mapNotification(response.data)
}

export async function markAllNotificationsRead() {
  const response = await apiClient.post<{ marked_read: number }>('/api/support/notifications/read-all/')
  return response.data
}

export async function getNotificationCount(): Promise<number> {
  const response = await apiClient.get<{ unread_count: number }>('/api/support/notifications/unread-count/')
  return response.data.unread_count
}
