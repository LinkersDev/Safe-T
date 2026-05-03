import { apiClient } from '../../../core/api/client'
import type { Account } from '../../accounts/types'

type BackendAccount = {
  id: number | string
  account_number: string
  account_name: string
  status: Account['status']
  available_balance: string | number
  ledger_balance?: string | number
  blocked_amount?: string | number
  currency: { code: string }
  owner_id?: number
  owner_name?: string
  owner_phone_number?: string
  owner_status?: string
  owner_kyc_status?: string
}

export type StaffAccountDetails = Account & {
  ledgerBalance?: number
  blockedAmount?: number
  owner?: {
    id?: number
    name?: string
    phoneNumber?: string
    status?: string
    kycStatus?: string
  }
}

function mapAccount(account: BackendAccount): StaffAccountDetails {
  return {
    id: String(account.id),
    accountNumber: account.account_number,
    balance: Number(account.available_balance),
    ledgerBalance: account.ledger_balance != null ? Number(account.ledger_balance) : undefined,
    blockedAmount: account.blocked_amount != null ? Number(account.blocked_amount) : undefined,
    currency: account.currency.code,
    status: account.status,
    label: account.account_name,
    owner: {
      id: account.owner_id,
      name: account.owner_name,
      phoneNumber: account.owner_phone_number,
      status: account.owner_status,
      kycStatus: account.owner_kyc_status,
    },
  }
}

export async function getStaffAccount(accountId: string) {
  const value = accountId.trim()

  // If caller passes numeric id, keep existing endpoint
  if (/^\d+$/.test(value)) {
    const response = await apiClient.get<BackendAccount>(`/api/staff/accounts/${value}/`)
    return mapAccount(response.data)
  }

  // Otherwise use lookup endpoint (phone number or account number)
  const isPhone = value.startsWith('+')
  const response = await apiClient.get<BackendAccount>('/api/staff/accounts/lookup/', {
    params: isPhone ? { phone_number: value, currency: 'USD' } : { account_number: value },
  })
  return mapAccount(response.data)
}

export async function freezeStaffAccount(accountId: string, reason: string) {
  return apiClient.post(`/api/staff/accounts/${accountId}/freeze/`, { reason })
}

export async function blockStaffAccount(accountId: string, reason: string) {
  return apiClient.post(`/api/staff/accounts/${accountId}/block/`, { reason })
}

export async function unblockStaffAccount(accountId: string, reason: string) {
  return apiClient.post(`/api/staff/accounts/${accountId}/unblock/`, { reason })
}

export async function unfreezeStaffAccount(accountId: string, reason: string) {
  return apiClient.post(`/api/staff/accounts/${accountId}/unfreeze/`, { reason })
}

export async function closeStaffAccount(accountId: string, reason: string) {
  return apiClient.post(`/api/staff/accounts/${accountId}/close/`, { reason })
}
