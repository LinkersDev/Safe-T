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
  mlFraudProbability: number | null
  ruleBasedScore: number | null
  combinedScore: number | null
  userName: string | null
  userPhone: string | null
  accountNumber: string | null
  txReference: string | null
  transactionType: string | null
  transactionAmount: string | null
  transactionCurrency: string | null
  loginDeviceId: string | null
  loginIpAddress: string | null
  loginLocation: string | null
  rulesTriggered: string[]
  autoActionTaken: string
  createdAt: string
  updatedAt: string
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
