import { apiClient } from '../../../core/api/client'
import { getMockTransactions } from '../../../core/mock/seed-bank-data'
import { isMockModeEnabled } from '../../../core/mock/mode'
import { getSessionState } from '../../../core/state/auth-state'
import type { LedgerListResponse, Transaction } from '../types'

type LedgerParams = {
  type?: string
  status?: string
  limit?: number
  offset?: number
}

type BackendTransaction = {
  id: number | string
  reference_number: string
  transaction_type: Transaction['type']
  status: Transaction['status']
  currency_code: string
  amount: string | number
  description: string
  occurred_at: string
  counterparty_display?: string
}

function mapTransaction(transaction: BackendTransaction): Transaction {
  return {
    id: String(transaction.id),
    reference: transaction.reference_number,
    amount: Number(transaction.amount),
    currency: transaction.currency_code,
    type: transaction.transaction_type,
    status: transaction.status,
    description: transaction.description,
    createdAt: transaction.occurred_at,
    counterpartyDisplay: transaction.counterparty_display,
  }
}

export async function getLedger(params?: LedgerParams) {
  const userId = getSessionState().user?.id

  if (isMockModeEnabled()) {
    return getMockTransactions(userId) satisfies LedgerListResponse
  }

  const response = await apiClient.get<BackendTransaction[]>('/api/ledger/transactions/', { params })
  return response.data.map(mapTransaction) satisfies LedgerListResponse
}

export async function getTransactionDetail(reference: string) {
  const userId = getSessionState().user?.id
  if (isMockModeEnabled()) {
    const transaction = getMockTransactions(userId).find((item) => item.reference === reference)
    if (transaction) {
      return transaction
    }
    const fallback = getMockTransactions(userId)[0]
    if (fallback) {
      return fallback
    }
    throw new Error('Mock transaction not found.')
  }

  const response = await apiClient.get<BackendTransaction>(`/api/ledger/transactions/${reference}/`)
  return mapTransaction(response.data)
}
