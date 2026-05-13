import { findMockUserById, mockSeedUsers } from './seed-users'

type MockAccount = {
  id: string
  accountNumber: string
  label: string
  currency: string
  balance: number
  status: 'ACTIVE' | 'FROZEN' | 'BLOCKED'
}

type MockTransaction = {
  id: string
  reference: string
  amount: number
  currency: string
  type: 'TRANSFER' | 'DEPOSIT' | 'WITHDRAWAL' | 'QR_PAYMENT' | 'BILL_PAYMENT'
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'REVERSED' | 'CANCELLED'
  description: string
  createdAt: string
  counterpartyDisplay?: string
  direction?: 'incoming' | 'outgoing'
}

type MockKycDocument = {
  id: number
  documentType: 'NATIONAL_ID' | 'PASSPORT' | 'RESIDENCE_PERMIT' | 'SELFIE' | 'PROOF_OF_ADDRESS'
  fileUrl: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED'
  rejectionReason: string
  createdAt: string
}

type MockKycState = {
  kycStatus: 'NOT_SUBMITTED' | 'PENDING' | 'APPROVED' | 'REJECTED'
  documents: MockKycDocument[]
}

const accountsByUserId = new Map<string, MockAccount[]>(
  mockSeedUsers.map((user) => [
    user.id,
    user.accounts.map((account, index) => ({
      id: account.id,
      accountNumber: `60000000000000${index + 1}`,
      label: `${user.fullName} Main Account`,
      currency: account.currency,
      balance: account.balance,
      status: 'ACTIVE',
    })),
  ]),
)

const now = new Date().toISOString()
const transactionsByUserId = new Map<string, MockTransaction[]>([
  [
    'mock-user-1',
    [
      {
        id: 'mock-tx-1',
        reference: 'MOCK-TRX-0001',
        amount: 220,
        currency: 'USD',
        type: 'TRANSFER',
        status: 'COMPLETED',
        description: 'Transfer to beneficiary',
        createdAt: now,
        counterpartyDisplay: 'To: Mock Teller',
        direction: 'outgoing',
      },
      {
        id: 'mock-tx-2',
        reference: 'MOCK-TRX-0002',
        amount: 75,
        currency: 'USD',
        type: 'QR_PAYMENT',
        status: 'PENDING',
        description: 'QR payment processing',
        createdAt: now,
        counterpartyDisplay: 'To: Test Shop',
        direction: 'outgoing',
      },
      {
        id: 'mock-tx-3',
        reference: 'MOCK-TRX-0003',
        amount: 130,
        currency: 'USD',
        type: 'BILL_PAYMENT',
        status: 'FAILED',
        description: 'Bill payment failed',
        createdAt: now,
        counterpartyDisplay: 'To: National Electricity',
        direction: 'outgoing',
      },
      {
        id: 'mock-tx-4',
        reference: 'MOCK-TRX-0004',
        amount: 90,
        currency: 'USD',
        type: 'TRANSFER',
        status: 'REVERSED',
        description: 'Reversed transfer',
        createdAt: now,
        counterpartyDisplay: 'To: Mock Admin',
        direction: 'outgoing',
      },
    ],
  ],
  ['mock-user-2', []],
  ['mock-user-3', []],
])

const kycByUserId = new Map<string, MockKycState>(
  mockSeedUsers.map((user) => [
    user.id,
    {
      kycStatus: user.kycStatus,
      documents: [],
    },
  ]),
)

export function getMockAccounts(userId: string | number | undefined) {
  return accountsByUserId.get(String(userId)) ?? []
}

export function getMockTransactions(userId: string | number | undefined) {
  return transactionsByUserId.get(String(userId)) ?? []
}

export function addMockTransaction(userId: string | number | undefined, transaction: MockTransaction) {
  const key = String(userId)
  const existing = transactionsByUserId.get(key) ?? []
  transactionsByUserId.set(key, [transaction, ...existing])
}

export function getMockKycState(userId: string | number | undefined): MockKycState {
  return (
    kycByUserId.get(String(userId)) ?? {
      kycStatus: 'NOT_SUBMITTED',
      documents: [],
    }
  )
}

export function addMockKycDocument(
  userId: string | number | undefined,
  document: Omit<MockKycDocument, 'id' | 'createdAt'>,
) {
  const key = String(userId)
  const current = getMockKycState(key)
  const nextDocument: MockKycDocument = {
    id: current.documents.length + 1,
    createdAt: new Date().toISOString(),
    ...document,
  }

  kycByUserId.set(key, {
    kycStatus: 'PENDING',
    documents: [nextDocument, ...current.documents],
  })
}

export function buildMockPaymentTransaction(params: {
  userId: string | number | undefined
  type: MockTransaction['type']
  amount: number
  description: string
  idempotencyKey: string
}) {
  const user = findMockUserById(params.userId)
  const account = user ? getMockAccounts(user.id)[0] : undefined
  const suffix = params.idempotencyKey.slice(0, 8).toUpperCase()

  const transaction: MockTransaction = {
    id: `mock-tx-${Date.now()}`,
    reference: `MOCK-${suffix}`,
    amount: params.amount,
    currency: account?.currency ?? 'USD',
    type: params.type,
    status: 'COMPLETED',
    description: params.description,
    createdAt: new Date().toISOString(),
    counterpartyDisplay: params.type === 'TRANSFER' ? 'To: Recipient' : undefined,
    direction: 'outgoing',
  }

  if (account) {
    account.balance = Math.max(0, account.balance - params.amount)
  }

  addMockTransaction(params.userId, transaction)
  return transaction
}
