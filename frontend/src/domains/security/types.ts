import type { RoleCode, SessionUser } from '../../core/state/auth-state'

export type SendOtpResponse = {
  message: string
  dev_otp?: string
  _debug_otp?: string
}

export type LoginRequest = {
  phoneNumber: string
  password?: string
  pin?: string
  otpCode?: string
}

export type LoginResponseUser = {
  id: number | string
  full_name: string
  phone_number: string
  status: SessionUser['status']
  role: RoleCode | null
  kyc_status?: SessionUser['kycStatus']
}

export type LoginResponse = {
  access: string
  refresh: string
  user: LoginResponseUser
  permissions?: string[]
}

export type MockAuthLoginResponse = {
  user: {
    id: string
    fullName: string
    role: 'customer' | 'teller' | 'admin'
    kycStatus: 'APPROVED' | 'PENDING' | 'REJECTED' | 'NOT_SUBMITTED'
  }
  otp_required: boolean
  session: {
    temp_token: string
    access_token: string
  }
}
