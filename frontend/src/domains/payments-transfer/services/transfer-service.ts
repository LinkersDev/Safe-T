import { apiClient } from '../../../core/api/client'
import { buildMockPaymentTransaction } from '../../../core/mock/seed-bank-data'
import { isMockModeEnabled } from '../../../core/mock/mode'
import { getSessionState } from '../../../core/state/auth-state'
import type { Transaction } from '../../ledger/types'
import type { TransferPayload } from '../types'

type RequestOtpResponse = {
  detail: string
  dev_otp?: string
  _debug_otp?: string
}

export type TransferRecipientPreview = {
  user_id: number | string
  full_name: string
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
  }
}

export async function requestTransferOtp() {
  if (isMockModeEnabled()) {
    return { detail: 'Mock OTP generated. Use 123456.', dev_otp: '123456' } satisfies RequestOtpResponse
  }

  const response = await apiClient.post<RequestOtpResponse>('/api/payments/transfer/otp/')
  return response.data
}

export async function lookupTransferRecipient(phone: string) {
  const response = await apiClient.get<TransferRecipientPreview>('/api/payments/transfer/recipient/', {
    params: { phone },
  })
  return response.data
}

export async function executeTransfer(payload: TransferPayload) {
  if (isMockModeEnabled()) {
    return buildMockPaymentTransaction({
      userId: getSessionState().user?.id,
      type: 'TRANSFER',
      amount: Number(payload.amount),
      description: payload.description || 'Mock transfer payment',
      idempotencyKey: payload.idempotencyKey,
    })
  }

  const response = await apiClient.post<BackendTransaction>('/api/payments/transfer/', {
    source_account_number: payload.sourceAccountNumber,
    destination_phone_number: payload.destinationPhoneNumber,
    amount: payload.amount,
    currency_code: payload.currencyCode,
    description: payload.description,
    pin: payload.pin,
    idempotency_key: payload.idempotencyKey,
  })
  return mapTransaction(response.data)
}
