import { apiClient } from '../../../core/api/client'
import { isMockModeEnabled } from '../../../core/mock/mode'
import { findMockUserByCredentials } from '../../../core/mock/seed-users'
import type { LoginRequest, LoginResponse, MockAuthLoginResponse, SendOtpResponse } from '../types'

function toMockRole(roleCode: string) {
  if (roleCode === 'ADMIN') return 'admin'
  if (roleCode === 'TELLER' || roleCode === 'TELLER_ADMIN') return 'teller'
  return 'customer'
}

export function isAuthMockMode() {
  return isMockModeEnabled()
}

export async function loginWithCredentials(
  phoneNumber: string,
  password: string,
): Promise<MockAuthLoginResponse> {
  if (!isAuthMockMode()) {
    const otpResponse = await sendLoginOtp(phoneNumber)
    const devOtp = otpResponse.dev_otp ?? otpResponse._debug_otp
    return {
      user: {
        id: 'pending-user',
        fullName: 'Pending verification',
        role: 'customer',
        kycStatus: 'PENDING',
      },
      otp_required: true,
      session: {
        temp_token: devOtp ?? 'pending-temp-token',
        access_token: '',
      },
    }
  }

  const mockUser = findMockUserByCredentials(phoneNumber, password)

  if (!mockUser) {
    throw new Error('Invalid credentials.')
  }

  const role = toMockRole(mockUser.roleCode)

  return {
    user: {
      id: mockUser.id,
      fullName: mockUser.fullName,
      role,
      kycStatus: mockUser.kycStatus,
    },
    otp_required: role === 'customer',
    session: {
      temp_token: 'mock-temp-token',
      access_token: 'mock-access-token',
    },
  }
}

export async function sendLoginOtp(phoneNumber: string) {
  const response = await apiClient.post<SendOtpResponse>('/api/auth/otp/send/', {
    phone_number: phoneNumber,
  })
  return response.data
}

export async function sendFirstLoginOtp(phoneNumber: string) {
  const response = await apiClient.post<SendOtpResponse>('/api/auth/first-login/otp/send/', {
    phone_number: phoneNumber,
  })
  return response.data
}

export async function completeFirstLogin(data: { phoneNumber: string; otpCode: string; password: string; pin: string }) {
  const response = await apiClient.post<LoginResponse>('/api/auth/first-login/complete/', {
    phone_number: data.phoneNumber,
    otp_code: data.otpCode,
    password: data.password,
    pin: data.pin,
  })
  return response.data
}

export async function loginWithOtp(payload: LoginRequest) {
  if (isAuthMockMode()) {
    const mockUser = findMockUserByCredentials(payload.phoneNumber, payload.password ?? '')
    if (!mockUser) {
      throw new Error('Invalid credentials.')
    }
    return {
      access: 'mock-access-token',
      refresh: 'mock-refresh-token',
      user: {
        id: mockUser.id,
        full_name: mockUser.fullName,
        phone_number: mockUser.phoneNumber,
        status: 'ACTIVE',
        role: mockUser.roleCode,
        kyc_status: mockUser.kycStatus,
      },
    } satisfies LoginResponse
  }

  const response = await apiClient.post<LoginResponse>('/api/auth/login/', {
    phone_number: payload.phoneNumber,
    password: payload.password,
    pin: payload.pin,
    otp_code: payload.otpCode,
  })
  return response.data
}
