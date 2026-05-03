import type { RoleCode } from '../../core/state/auth-state'
import type { KycDocument, KycStatus } from '../kyc/types'
import type { SupportTicket } from '../support/types'
import type { Transaction } from '../ledger/types'

export type StaffUser = {
  id: number
  fullName: string
  phoneNumber: string
  status: string
  kycStatus: KycStatus
  /** Django login flag; false after failed-attempt auto-lock (status may still be ACTIVE). */
  isActive: boolean
  role: { code: RoleCode; name: string } | null
  createdAt: string
}

export type KycReviewUser = {
  id: number
  fullName: string
  phoneNumber: string
  kycStatus: KycStatus
  pendingDocumentCount: number
}

export type FraudAlert = {
  id: number
  alertType: string
  severity: string
  status: string
  riskScore: string
  userName: string | null
  accountNumber: string | null
  txReference: string | null
  createdAt: string
}

export type AdminSummary = {
  total_users?: number
  active_users?: number
  pending_users?: number
  blocked_users?: number
  total_transaction_count?: number
  total_transaction_volume?: string
}

export type OperationsSummary = {
  pending_kyc_users?: number
  pending_kyc_docs?: number
  open_support_tickets?: number
  unassigned_tickets?: number
  transactions_last_hour?: number
}

export type StaffKycDocument = KycDocument
export type StaffSupportTicket = SupportTicket & {
  customerId?: number
  customerName?: string | null
  customerPhoneNumber?: string | null
}
export type StaffTransaction = Transaction
