import type { RoleCode } from '../state/auth-state'

export type MockSeedUser = {
  id: string
  phoneNumber: string
  password: string
  fullName: string
  role: 'customer' | 'teller' | 'admin'
  roleCode: RoleCode
  kycStatus: 'NOT_SUBMITTED' | 'PENDING' | 'APPROVED' | 'REJECTED'
  accounts: Array<{
    id: string
    balance: number
    currency: string
  }>
}

export const mockSeedUsers: MockSeedUser[] = [
  {
    id: 'mock-user-1',
    phoneNumber: '+966500000001',
    password: 'Customer@123',
    fullName: 'Mock Customer',
    role: 'customer',
    roleCode: 'CUSTOMER',
    kycStatus: 'APPROVED',
    accounts: [{ id: 'mock-acc-customer-1', balance: 12500.5, currency: 'USD' }],
  },
  {
    id: 'mock-user-2',
    phoneNumber: '+966500000002',
    password: 'Teller@123',
    fullName: 'Mock Teller',
    role: 'teller',
    roleCode: 'TELLER',
    kycStatus: 'APPROVED',
    accounts: [{ id: 'mock-acc-teller-1', balance: 0, currency: 'USD' }],
  },
  {
    id: 'mock-user-3',
    phoneNumber: '+966500000003',
    password: 'Admin@123',
    fullName: 'Mock Admin',
    role: 'admin',
    roleCode: 'ADMIN',
    kycStatus: 'APPROVED',
    accounts: [{ id: 'mock-acc-admin-1', balance: 0, currency: 'USD' }],
  },
]

export function findMockUserByCredentials(phoneNumber: string, password: string) {
  return mockSeedUsers.find((user) => user.phoneNumber === phoneNumber && user.password === password)
}

export function findMockUserById(userId: string | number | undefined) {
  if (!userId) {
    return null
  }
  return mockSeedUsers.find((user) => user.id === String(userId)) ?? null
}
