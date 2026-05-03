import { apiClient } from '../../../core/api/client'

export type TellerRegisterPayload = {
  full_name: string
  phone_number: string
  legal_full_name: string
  date_of_birth: string
  nationality: string
  id_type: 'NATIONAL_ID' | 'PASSPORT' | 'RESIDENCE_PERMIT'
  id_number: string
  address_line1: string
  address_city: string
  address_country: string
  document_type: 'NATIONAL_ID' | 'PASSPORT' | 'RESIDENCE_PERMIT'
  file: File
}

export async function registerCustomer(payload: TellerRegisterPayload) {
  const form = new FormData()
  form.append('full_name', payload.full_name)
  form.append('phone_number', payload.phone_number)
  form.append('legal_full_name', payload.legal_full_name)
  form.append('date_of_birth', payload.date_of_birth)
  form.append('nationality', payload.nationality)
  form.append('id_type', payload.id_type)
  form.append('id_number', payload.id_number)
  form.append('address_line1', payload.address_line1)
  form.append('address_city', payload.address_city)
  form.append('address_country', payload.address_country)
  form.append('document_type', payload.document_type)
  form.append('file', payload.file)

  const response = await apiClient.post('/api/staff/teller/customers/register/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data as {
    user: { id: number | string; full_name: string; phone_number: string; status: string; kyc_status: string }
    account: any
    onboarding: { first_login_completed: boolean; next_step: string }
  }
}

export async function tellerDeposit(payload: { lookup: string; amount: number | string; currency?: string; description?: string }) {
  const response = await apiClient.post('/api/staff/teller/transactions/deposit/', payload)
  return response.data as { transaction: { reference_number: string; status: string } }
}

export async function tellerWithdraw(payload: { lookup: string; amount: number | string; currency?: string; description?: string }) {
  const response = await apiClient.post('/api/staff/teller/transactions/withdraw/', payload)
  return response.data as { transaction: { reference_number: string; status: string } }
}

export type TellerTx = {
  id: number
  reference_number: string
  transaction_type: string
  status: string
  currency_code: string
  amount: string | number
  description: string
  occurred_at: string
}

export async function getAccountTransactions(accountId: string | number, limit = 50) {
  const response = await apiClient.get(`/api/staff/teller/accounts/${accountId}/transactions/`, { params: { limit } })
  return response.data as TellerTx[]
}

export type TellerCustomerProfile = {
  user: { id: number | string; full_name: string; phone_number: string; status: string; kyc_status: string }
  accounts: any[]
  kyc: {
    profile: any | null
    documents: any[]
    completeness: { is_valid: boolean; missing_fields: string[]; missing_documents: string[] }
  }
}

export async function getCustomerProfile(userId: number | string) {
  const response = await apiClient.get(`/api/staff/teller/customers/${userId}/profile/`)
  return response.data as TellerCustomerProfile
}

export async function submitCustomerKycProfile(userId: number | string, payload: Record<string, any>) {
  const response = await apiClient.post(`/api/staff/teller/customers/${userId}/kyc-profile/submit/`, payload)
  return response.data as any
}

export async function uploadCustomerKycDocument(userId: number | string, payload: { document_type: string; file: File }) {
  const form = new FormData()
  form.append('document_type', payload.document_type)
  form.append('file', payload.file)
  const response = await apiClient.post(`/api/staff/teller/customers/${userId}/documents/upload/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data as any
}

export async function lookupCustomerByPhone(phone: string) {
  const response = await apiClient.get('/api/staff/teller/customers/lookup/', { params: { phone } })
  return response.data as { user_id: number }
}

