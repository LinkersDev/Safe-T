import type {
  AdminSummary,
  FraudAlert,
  KycReviewUser,
  OperationsSummary,
  StaffSupportTicket,
  StaffTransaction,
  StaffUser,
} from '../../../domains/staff/types'

export type BackendStaffUser = {
  id: number
  full_name: string
  phone_number: string
  status: string
  kyc_status: StaffUser['kycStatus']
  is_active?: boolean
  role: StaffUser['role']
  created_at: string
}

export type BackendKycUser = {
  id: number
  full_name: string
  phone_number: string
  kyc_status: KycReviewUser['kycStatus']
  pending_document_count: number
}

export type BackendTicket = {
  id: number
  subject: string
  category: StaffSupportTicket['category']
  status: StaffSupportTicket['status']
  user_id?: number
  user_full_name?: string | null
  user_phone_number?: string | null
  assigned_to_name: string | null
  created_at: string
  updated_at: string
}

export type BackendTransaction = {
  id: number | string
  reference_number: string
  transaction_type: StaffTransaction['type']
  status: StaffTransaction['status']
  currency_code: string
  amount: string | number
  description: string
  occurred_at: string
}

export type BackendAlert = {
  id: number
  alert_type: string
  severity: string
  status: string
  risk_score: string
  user_name: string | null
  account_number: string | null
  tx_reference: string | null
  created_at: string
}

export type BackendKycDocument = {
  id: number
  document_type: string
  status: string
  file?: string
  rejection_reason?: string | null
  created_at: string
}

export type StaffKycDocument = {
  id: number
  documentType: string
  status: string
  fileUrl?: string
  rejectionReason?: string | null
  submittedAt: string
}

export type BackendStaffTicketMessage = {
  id: number
  sender_name: string | null
  body: string
  is_internal: boolean
  created_at: string
}

export type BackendStaffTicketDetail = {
  id: number
  subject: string
  category: StaffSupportTicket['category']
  status: StaffSupportTicket['status']
  user_id?: number
  user_full_name?: string | null
  user_phone_number?: string | null
  assigned_to_name: string | null
  created_at: string
  updated_at: string
  messages: BackendStaffTicketMessage[]
}

export type StaffTicketMessage = {
  id: number
  senderName: string | null
  body: string
  isInternal: boolean
  createdAt: string
}

export type StaffTicketDetail = StaffSupportTicket & {
  messages: StaffTicketMessage[]
}

export function mapStaffUser(user: BackendStaffUser): StaffUser {
  return {
    id: user.id,
    fullName: user.full_name,
    phoneNumber: user.phone_number,
    status: user.status,
    kycStatus: user.kyc_status,
    isActive: user.is_active ?? true,
    role: user.role,
    createdAt: user.created_at,
  }
}

export function mapStaffUsers(users: BackendStaffUser[]): StaffUser[] {
  return users.map(mapStaffUser)
}

export function mapKycUser(user: BackendKycUser): KycReviewUser {
  return {
    id: user.id,
    fullName: user.full_name,
    phoneNumber: user.phone_number,
    kycStatus: user.kyc_status,
    pendingDocumentCount: user.pending_document_count,
  }
}

export function mapKycUsers(users: BackendKycUser[]): KycReviewUser[] {
  return users.map(mapKycUser)
}

export function mapStaffTicket(ticket: BackendTicket): StaffSupportTicket {
  return {
    id: ticket.id,
    subject: ticket.subject,
    category: ticket.category,
    status: ticket.status,
    customerId: ticket.user_id,
    customerName: ticket.user_full_name ?? null,
    customerPhoneNumber: ticket.user_phone_number ?? null,
    assignedToName: ticket.assigned_to_name,
    createdAt: ticket.created_at,
    updatedAt: ticket.updated_at,
  }
}

export function mapStaffTickets(tickets: BackendTicket[]): StaffSupportTicket[] {
  return tickets.map(mapStaffTicket)
}

export function mapTransaction(transaction: BackendTransaction): StaffTransaction {
  return {
    id: String(transaction.id),
    reference: transaction.reference_number,
    amount: Number(transaction.amount),
    currency: transaction.currency_code,
    type: transaction.transaction_type,
    status: transaction.status,
    description: transaction.description,
    createdAt: transaction.occurred_at,
  }
}

export function mapTransactions(transactions: BackendTransaction[]): StaffTransaction[] {
  return transactions.map(mapTransaction)
}

export function mapRiskAlert(alert: BackendAlert): FraudAlert {
  return {
    id: alert.id,
    alertType: alert.alert_type,
    severity: alert.severity,
    status: alert.status,
    riskScore: alert.risk_score,
    userName: alert.user_name,
    accountNumber: alert.account_number,
    txReference: alert.tx_reference,
    createdAt: alert.created_at,
  }
}

export function mapRiskAlerts(alerts: BackendAlert[]): FraudAlert[] {
  return alerts.map(mapRiskAlert)
}

export function mapKycDocument(doc: BackendKycDocument): StaffKycDocument {
  return {
    id: doc.id,
    documentType: doc.document_type,
    status: doc.status,
    fileUrl: doc.file,
    rejectionReason: doc.rejection_reason,
    submittedAt: doc.created_at,
  }
}

export function mapKycDocuments(docs: BackendKycDocument[]): StaffKycDocument[] {
  return docs.map(mapKycDocument)
}

export function mapStaffTicketDetail(ticket: BackendStaffTicketDetail): StaffTicketDetail {
  return {
    id: ticket.id,
    subject: ticket.subject,
    category: ticket.category,
    status: ticket.status,
    customerId: ticket.user_id,
    customerName: ticket.user_full_name ?? null,
    customerPhoneNumber: ticket.user_phone_number ?? null,
    assignedToName: ticket.assigned_to_name,
    createdAt: ticket.created_at,
    updatedAt: ticket.updated_at,
    messages: ticket.messages.map((m) => ({
      id: m.id,
      senderName: m.sender_name,
      body: m.body,
      isInternal: m.is_internal,
      createdAt: m.created_at,
    })),
  }
}

export function mapAdminSummary(response: AdminSummary): AdminSummary {
  return response
}

export function mapOperationsSummary(response: OperationsSummary): OperationsSummary {
  return response
}

export function mapUserGrowth(response: {
  days: number
  rows: Array<{ day: string; new_users: number }>
}) {
  return response.rows.map((row) => ({ date: row.day, count: row.new_users }))
}

export function mapTransactionVolume(response: {
  period: 'daily' | 'weekly'
  days?: number
  weeks?: number
  rows: Array<{ day?: string; week?: string; count: number; volume: string | number }>
}) {
  return response.rows.map((row) => ({
    date: row.day ?? row.week ?? '',
    total: Number(row.volume),
    count: row.count,
  }))
}

export function mapTransactionsByType(response: {
  days: number
  rows: Array<{ transaction_type: string; count: number; volume: string | number }>
}) {
  return response.rows.map((row) => ({
    type: row.transaction_type,
    count: row.count,
    total: Number(row.volume),
  }))
}

export function mapRiskSummary(response: {
  by_severity: Record<string, number>
  total_alerts: number
  open_alerts: number
  auto_actioned: number
}) {
  return {
    total_alerts: response.total_alerts,
    open_alerts: response.open_alerts,
    critical_alerts: response.by_severity?.CRITICAL ?? 0,
    dismissed_today: response.auto_actioned ?? 0,
  }
}

export function mapRecentTransactions(response: Array<{
  reference_number: string
  transaction_type: StaffTransaction['type']
  status: StaffTransaction['status']
  amount: string | number
  currency: string
  occurred_at: string
}>) {
  return response.map((transaction, idx) => ({
    id: `${transaction.reference_number}-${idx}`,
    reference: transaction.reference_number,
    amount: Number(transaction.amount),
    currency: transaction.currency,
    type: transaction.transaction_type,
    status: transaction.status,
    description: transaction.transaction_type.replace(/_/g, ' '),
    createdAt: transaction.occurred_at,
  }))
}
