export type TransactionStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'
  | 'REVERSED'
  | 'CANCELLED'

export type TransactionType =
  | 'TRANSFER'
  | 'DEPOSIT'
  | 'WITHDRAWAL'
  | 'QR_PAYMENT'
  | 'BILL_PAYMENT'

export type Transaction = {
  id: string
  reference: string
  amount: number
  currency: string
  type: TransactionType
  status: TransactionStatus
  description: string
  createdAt: string
  /** e.g. "To: Jane Doe" / "From: Branch teller name" */
  counterpartyDisplay?: string
  /** 'incoming' = money received by user, 'outgoing' = money sent by user */
  direction?: 'incoming' | 'outgoing'
}

export type LedgerListResponse = Transaction[]
