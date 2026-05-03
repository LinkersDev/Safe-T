import type { Transaction } from '../ledger/types'

export type BillProvider = {
  code: string
  name: string
  serviceType: string
}

export type BillInfo = {
  provider_code: string
  service_number: string
  bill_reference: string
  amount: string
}

export type BillPayPayload = {
  providerCode: string
  serviceNumber: string
  billReference: string
  sourceAccountNumber: string
  amount: string
  otpCode: string
  idempotencyKey: string
}

export type BillPayResult = Transaction
