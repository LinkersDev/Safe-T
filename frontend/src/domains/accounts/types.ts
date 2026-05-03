export type AccountStatus = 'ACTIVE' | 'FROZEN' | 'BLOCKED' | 'CLOSED'

export type Account = {
  id: string
  accountNumber: string
  balance: number
  currency: string
  status: AccountStatus
  label: string
}

export type AccountsListResponse = Account[]
