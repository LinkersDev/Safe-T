import { apiClient } from '../../../core/api/client'
import { getMockAccounts } from '../../../core/mock/seed-bank-data'
import { isMockModeEnabled } from '../../../core/mock/mode'
import { getSessionState } from '../../../core/state/auth-state'
import type { AccountsListResponse, Account } from '../types'

type BackendAccount = {
  id: number | string
  account_number: string
  account_name: string
  status: Account['status']
  available_balance: string | number
  currency: {
    code: string
  }
}

function mapAccount(account: BackendAccount): Account {
  return {
    id: String(account.id),
    accountNumber: account.account_number,
    balance: Number(account.available_balance),
    currency: account.currency.code,
    status: account.status,
    label: account.account_name,
  }
}

export async function getAccounts() {
  const userId = getSessionState().user?.id

  if (isMockModeEnabled()) {
    return getMockAccounts(userId) satisfies AccountsListResponse
  }

  try {
    const response = await apiClient.get<BackendAccount[]>('/api/accounts/')
    return response.data.map(mapAccount) satisfies AccountsListResponse
  } catch {
    if (isMockModeEnabled()) {
      return getMockAccounts(userId) satisfies AccountsListResponse
    }
    throw new Error('Failed to load accounts.')
  }
}

export async function getAccountDetail(id: string) {
  const userId = getSessionState().user?.id
  const mockAccount = getMockAccounts(userId).find((account) => account.id === id)

  if (isMockModeEnabled()) {
    if (mockAccount) {
      return mockAccount
    }

    const fallback = getMockAccounts(userId)[0]
    if (fallback) {
      return fallback
    }
    throw new Error('Mock account not found.')
  }

  const response = await apiClient.get<BackendAccount>(`/api/accounts/${id}/`)
  return mapAccount(response.data)
}
