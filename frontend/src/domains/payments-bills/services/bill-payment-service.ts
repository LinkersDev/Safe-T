import { apiClient } from '../../../core/api/client'
import { buildMockPaymentTransaction } from '../../../core/mock/seed-bank-data'
import { isMockModeEnabled } from '../../../core/mock/mode'
import { getSessionState } from '../../../core/state/auth-state'
import type { Transaction } from '../../ledger/types'
import type { BillInfo, BillPayPayload, BillProvider } from '../types'

type RequestOtpResponse = {
  detail: string
  dev_otp?: string
  _debug_otp?: string
}

type BackendBillProvider = {
  code: string
  name: string
  service_type: string
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

function mapProvider(provider: BackendBillProvider): BillProvider {
  return {
    code: provider.code,
    name: provider.name,
    serviceType: provider.service_type,
  }
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

export async function getBillProviders() {
  if (isMockModeEnabled()) {
    return [
      { code: 'ELEC', name: 'Electricity Company', serviceType: 'UTILITY' },
      { code: 'WATER', name: 'Water Services', serviceType: 'UTILITY' },
    ]
  }

  const response = await apiClient.get<BackendBillProvider[]>('/api/payments/bill/providers/')
  return response.data.map(mapProvider)
}

export async function fetchBill(providerCode: string, serviceNumber: string) {
  if (isMockModeEnabled()) {
    return {
      provider_code: providerCode,
      service_number: serviceNumber,
      bill_reference: `MOCK-BILL-${serviceNumber.slice(-4)}`,
      amount: '135.50',
    }
  }

  const response = await apiClient.post<BillInfo>('/api/payments/bill/fetch/', {
    provider_code: providerCode,
    service_number: serviceNumber,
  })
  return response.data
}

export async function requestBillPaymentOtp(providerCode: string, serviceNumber: string) {
  if (isMockModeEnabled()) {
    return {
      detail: `Mock OTP generated for ${providerCode}/${serviceNumber}. Use 123456.`,
      dev_otp: '123456',
    } satisfies RequestOtpResponse
  }

  const response = await apiClient.post<RequestOtpResponse>('/api/payments/bill/otp/', {
    provider_code: providerCode,
    service_number: serviceNumber,
  })
  return response.data
}

export async function executeBillPayment(payload: BillPayPayload) {
  if (isMockModeEnabled()) {
    return buildMockPaymentTransaction({
      userId: getSessionState().user?.id,
      type: 'BILL_PAYMENT',
      amount: Number(payload.amount),
      description: `Mock bill payment ${payload.billReference}`,
      idempotencyKey: payload.idempotencyKey,
    })
  }

  const response = await apiClient.post<BackendTransaction>('/api/payments/bill/pay/', {
    provider_code: payload.providerCode,
    service_number: payload.serviceNumber,
    bill_reference: payload.billReference,
    source_account_number: payload.sourceAccountNumber,
    amount: payload.amount,
    otp_code: payload.otpCode,
    idempotency_key: payload.idempotencyKey,
  })
  return mapTransaction(response.data)
}
