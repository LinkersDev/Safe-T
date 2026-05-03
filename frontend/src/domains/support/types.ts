export type TicketStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED'
export type TicketCategory =
  | 'ACCOUNT_ISSUE'
  | 'PAYMENT_ISSUE'
  | 'KYC_ISSUE'
  | 'CARD_ISSUE'
  | 'GENERAL'
  | 'OTHER'

export type SupportTicket = {
  id: number
  subject: string
  category: TicketCategory
  status: TicketStatus
  assignedToName: string | null
  createdAt: string
  updatedAt: string
}

export type SupportTicketMessage = {
  id: number
  senderName: string | null
  body: string
  isInternal: boolean
  createdAt: string
}

export type SupportTicketDetail = SupportTicket & {
  messages: SupportTicketMessage[]
}

export type Notification = {
  id: number
  notificationType: string
  title: string
  message: string
  isRead: boolean
  referenceType: string
  referenceId: string
  createdAt: string
}
