import type { Transaction } from '../ledger/types'

/** Passed when navigating from peer QR scan → Send Money. */
export type TransferRoutePrefill = {
  fromQrScan?: boolean
  destinationPhoneNumber?: string
  destinationAccountNumber?: string
  recipientFullName?: string
}

export type TransferPayload = {
  sourceAccountNumber: string
  destinationPhoneNumber: string
  amount: string
  currencyCode: string
  description: string
  pin: string
  idempotencyKey: string
}

export type TransferResult = Transaction
