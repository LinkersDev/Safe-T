import { apiClient } from '../../../core/api/client'
import type {
  AdminSummary,
  OperationsSummary,
  StaffTransaction,
} from '../types'
import {
  mapAdminSummary,
  mapKycDocuments,
  mapKycUsers,
  mapOperationsSummary,
  mapRecentTransactions,
  mapRiskAlerts,
  mapRiskSummary,
  mapStaffTicketDetail,
  mapStaffTickets,
  mapStaffUser,
  mapStaffUsers,
  mapTransactions,
  mapTransactionsByType,
  mapTransactionVolume,
  mapUserGrowth,
  type BackendAlert,
  type BackendKycDocument,
  type BackendKycUser,
  type BackendStaffTicketDetail,
  type BackendStaffUser,
  type BackendTicket,
  type BackendTransaction,
  type StaffTicketDetail,
} from '../../../core/api/mappers/staff-mappers'

export type { StaffKycDocument } from '../../../core/api/mappers/staff-mappers'

export async function getPendingUsers() {
  const response = await apiClient.get<BackendStaffUser[]>('/api/staff/users/pending/')
  return mapStaffUsers(response.data)
}

export async function getAllUsers(params?: { search?: string; limit?: number }) {
  const response = await apiClient.get<BackendStaffUser[]>('/api/staff/users/', {
    params: {
      search: params?.search ?? '',
      limit: params?.limit ?? 500,
    },
  })
  return mapStaffUsers(response.data)
}

export async function approveUser(userId: number) {
  const response = await apiClient.post<BackendStaffUser>(`/api/staff/users/${userId}/approve/`)
  return mapStaffUser(response.data)
}

export async function rejectUser(userId: number, reason: string) {
  const response = await apiClient.post<BackendStaffUser>(`/api/staff/users/${userId}/reject/`, { reason })
  return mapStaffUser(response.data)
}

export async function getPendingKycUsers() {
  const response = await apiClient.get<BackendKycUser[]>('/api/staff/kyc/pending/')
  return mapKycUsers(response.data)
}

export async function approveKycUser(userId: number) {
  return apiClient.post(`/api/staff/kyc/users/${userId}/approve/`)
}

export async function rejectKycUser(userId: number, reason: string) {
  return apiClient.post(`/api/staff/kyc/users/${userId}/reject/`, { reason })
}

export async function registerStaff(payload: {
  full_name: string
  phone_number: string
  role_code: string
  employee_id?: string
  department?: string
  branch?: string
  job_title?: string
  address_line1?: string
  address_city?: string
  address_country?: string
}) {
  const response = await apiClient.post('/api/staff/users/staff/register/', payload)
  return response.data as {
    user: any
    onboarding: { first_login_completed: boolean; next_step: string }
  }
}

export async function getStaffTransactions(params?: {
  q?: string
  from?: string
  to?: string
  type?: string
  status?: string
  currency?: string
  limit?: number
  offset?: number
}) {
  const response = await apiClient.get<BackendTransaction[]>('/api/staff/ledger/transactions/', { params })
  return mapTransactions(response.data)
}

type BackendStaffTransactionDetailEntry = {
  id: number
  entry_type: string
  amount: string | number
  sequence_no: number
  account_id: number
  account_number: string
  account_owner_name?: string | null
  account_owner_phone?: string | null
  created_at: string
}

type BackendStaffTransactionDetail = {
  id: number | string
  reference_number: string
  transaction_type: StaffTransaction['type']
  status: StaffTransaction['status']
  currency_code: string
  amount: string | number
  description: string
  channel: string
  occurred_at: string
  completed_at?: string | null
  reversed_at?: string | null
  teller_operation?: string | null
  entries: BackendStaffTransactionDetailEntry[]
}

export type StaffTransactionDetail = {
  id: string
  reference: string
  type: StaffTransaction['type']
  status: StaffTransaction['status']
  currency: string
  amount: number
  description: string
  channel: string
  occurredAt: string
  completedAt?: string | null
  reversedAt?: string | null
  tellerOperation?: string | null
  entries: Array<{
    id: number
    entryType: string
    amount: number
    sequenceNo: number
    accountId: number
    accountNumber: string
    ownerName?: string | null
    ownerPhone?: string | null
    createdAt: string
  }>
}

export async function getStaffTransactionDetail(reference: string) {
  const response = await apiClient.get<BackendStaffTransactionDetail>(`/api/staff/ledger/transactions/${reference}/`)
  const d = response.data
  return {
    id: String(d.id),
    reference: d.reference_number,
    type: d.transaction_type,
    status: d.status,
    currency: d.currency_code,
    amount: Number(d.amount),
    description: d.description,
    channel: d.channel,
    occurredAt: d.occurred_at,
    completedAt: d.completed_at ?? null,
    reversedAt: d.reversed_at ?? null,
    tellerOperation: d.teller_operation ?? null,
    entries: (d.entries ?? []).map((e) => ({
      id: e.id,
      entryType: e.entry_type,
      amount: Number(e.amount),
      sequenceNo: e.sequence_no,
      accountId: e.account_id,
      accountNumber: e.account_number,
      ownerName: e.account_owner_name ?? null,
      ownerPhone: e.account_owner_phone ?? null,
      createdAt: e.created_at,
    })),
  } satisfies StaffTransactionDetail
}

export async function reverseStaffTransaction(reference: string, reason: string) {
  const response = await apiClient.post<BackendTransaction>(
    `/api/staff/ledger/transactions/${reference}/reverse/`,
    { reason },
  )
  return mapTransactions([response.data])[0]
}

export async function getStaffSupportTickets(params?: { status?: string; unassigned?: boolean }) {
  const response = await apiClient.get<BackendTicket[]>('/api/staff/support/tickets/', {
    params: {
      status: params?.status,
      unassigned: params?.unassigned ? '1' : undefined,
    },
  })
  return mapStaffTickets(response.data)
}

export async function assignStaffTicket(ticketId: number) {
  return apiClient.post(`/api/staff/support/tickets/${ticketId}/assign/`)
}

export async function resolveStaffTicket(ticketId: number) {
  return apiClient.post(`/api/staff/support/tickets/${ticketId}/resolve/`)
}

export async function getRiskAlerts() {
  const response = await apiClient.get<BackendAlert[]>('/api/staff/risk/alerts/')
  return mapRiskAlerts(response.data)
}

export async function dismissRiskAlert(alertId: number) {
  return apiClient.post(`/api/staff/risk/alerts/${alertId}/dismiss/`)
}

export type RiskAlertAction = 'DISMISS' | 'WARN' | 'FREEZE_ACCOUNT' | 'BLOCK_ACCOUNT' | 'ESCALATE'

export async function reviewRiskAlert(alertId: number, action: RiskAlertAction, notes?: string) {
  return apiClient.post(`/api/staff/risk/alerts/${alertId}/review/`, { action, notes })
}

export async function unlockUser(userId: number) {
  return apiClient.post(`/api/staff/users/${userId}/unlock/`)
}

export async function getStaffKycUserDocuments(userId: number) {
  const response = await apiClient.get<BackendKycDocument[]>(`/api/staff/kyc/users/${userId}/documents/`)
  return mapKycDocuments(response.data)
}

export async function approveKycDocument(docId: number) {
  return apiClient.post(`/api/staff/kyc/documents/${docId}/approve/`)
}

export async function rejectKycDocument(docId: number, reason: string) {
  return apiClient.post(`/api/staff/kyc/documents/${docId}/reject/`, { reason })
}

export async function getStaffTicketDetail(ticketId: number | string): Promise<StaffTicketDetail> {
  const response = await apiClient.get<BackendStaffTicketDetail>(`/api/staff/support/tickets/${ticketId}/`)
  return mapStaffTicketDetail(response.data)
}

export async function replyStaffTicket(ticketId: number | string, body: string, opts?: { isInternal?: boolean }) {
  return apiClient.post(`/api/staff/support/tickets/${ticketId}/reply/`, {
    body,
    is_internal: opts?.isInternal ?? false,
  })
}

export async function getAdminSummary() {
  const response = await apiClient.get<AdminSummary>('/api/staff/reports/admin/summary/')
  return mapAdminSummary(response.data)
}

export async function getOperationsSummary() {
  const response = await apiClient.get<OperationsSummary>('/api/staff/reports/operations/summary/')
  return mapOperationsSummary(response.data)
}

export async function getUserGrowth() {
  const response = await apiClient.get<{
    days: number
    rows: Array<{ day: string; new_users: number }>
  }>('/api/staff/reports/admin/users/growth/')
  return mapUserGrowth(response.data)
}

export async function getTransactionVolume() {
  const response = await apiClient.get<{
    period: 'daily' | 'weekly'
    days?: number
    weeks?: number
    rows: Array<{ day?: string; week?: string; count: number; volume: string | number }>
  }>('/api/staff/reports/admin/transactions/volume/')
  return mapTransactionVolume(response.data)
}

export async function getTransactionsByType() {
  const response = await apiClient.get<{
    days: number
    rows: Array<{ transaction_type: string; count: number; volume: string | number }>
  }>('/api/staff/reports/admin/transactions/by-type/')
  return mapTransactionsByType(response.data)
}

export async function getRiskSummary() {
  const response = await apiClient.get<{
    by_severity: Record<string, number>
    total_alerts: number
    open_alerts: number
    auto_actioned: number
  }>('/api/staff/reports/risk/summary/')
  return mapRiskSummary(response.data)
}

export async function getRecentTransactions() {
  const response = await apiClient.get<
    Array<{
      reference_number: string
      transaction_type: StaffTransaction['type']
      status: StaffTransaction['status']
      amount: string | number
      currency: string
      occurred_at: string
    }>
  >('/api/staff/reports/operations/transactions/recent/')
  return mapRecentTransactions(response.data)
}
