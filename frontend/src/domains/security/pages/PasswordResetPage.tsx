import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '../../../core/api/client'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { DevOtpCard } from '../../../shared/components/ui/DevOtpCard'
import type { SendOtpResponse } from '../types'
import { isAuthMockMode } from '../services/auth-service'

type Step = 'phone' | 'otp' | 'password' | 'done'

async function sendPasswordResetOtp(phoneNumber: string): Promise<SendOtpResponse> {
  if (isAuthMockMode()) {
    return {
      message: 'Demo: use OTP below.',
      dev_otp: '123456',
    }
  }
  const response = await apiClient.post<SendOtpResponse>('/api/auth/reset-password/', {
    phone_number: phoneNumber,
  })
  return response.data
}

async function confirmPasswordReset(data: {
  phoneNumber: string
  otpCode: string
  newPassword: string
}) {
  if (isAuthMockMode()) {
    const code = data.otpCode.replace(/\D/g, '')
    if (code !== '123456') {
      throw new Error('Invalid OTP code.')
    }
    return { message: 'Password updated successfully.' }
  }
  const response = await apiClient.post<{ detail: string }>('/api/auth/reset-password/confirm/', {
    phone_number: data.phoneNumber,
    otp_code: data.otpCode,
    new_password: data.newPassword,
  })
  return response.data
}

export function PasswordResetPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [step, setStep] = useState<Step>('phone')
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [debugOtp, setDebugOtp] = useState<string | null>(null)

  useEffect(() => {
    const s = location.state as { phoneNumber?: string } | null | undefined
    if (!s?.phoneNumber) return
    setPhone(s.phoneNumber)
    navigate(location.pathname, { replace: true, state: {} })
  }, [location.state, location.pathname, navigate])

  const sendOtpMutation = useMutation({
    mutationFn: sendPasswordResetOtp,
    onSuccess: (data) => {
      const next = data.dev_otp ?? data._debug_otp ?? null
      setDebugOtp(next ?? null)
      setStep('otp')
    },
    onError: () => setError('Could not send OTP. Check your phone number.'),
  })

  const confirmMutation = useMutation({
    mutationFn: confirmPasswordReset,
    onSuccess: () => setStep('done'),
    onError: (err: unknown) => {
      const msg = err instanceof Error && err.message ? err.message : 'Reset failed. Check your OTP or try again.'
      setError(msg)
    },
  })

  function handlePhoneSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setDebugOtp(null)
    if (!phone.trim()) return
    sendOtpMutation.mutate(phone.trim())
  }

  function handleOtpSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!otp.trim()) return
    setStep('password')
  }

  function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    confirmMutation.mutate({ phoneNumber: phone, otpCode: otp, newPassword })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-secondary px-4">
      <div className="w-full max-w-sm space-y-6 rounded-2xl border border-border bg-surface-primary p-8 shadow-sm">
        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2">
          {(['phone', 'otp', 'password'] as Step[]).map((s, idx) => (
            <div
              key={s}
              className={`h-2 w-2 rounded-full transition-colors ${
                step === s || (step === 'done' && idx < 3) ? 'bg-indigo-600' : 'bg-border'
              }`}
            />
          ))}
        </div>

        {step === 'phone' && (
          <form onSubmit={handlePhoneSubmit} className="space-y-5">
            <div>
              <h1 className="text-xl font-bold text-text-primary">Reset password</h1>
              <p className="mt-1 text-sm text-text-secondary">
                Enter your registered phone number to receive a reset code.
              </p>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Phone number</label>
              <input
                type="tel"
                placeholder="+252XXXXXXXXX"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full rounded-lg border border-border bg-surface-secondary px-3 py-2.5 text-sm text-text-primary outline-none focus:border-indigo-500"
                required
              />
            </div>
            {error && <p className="text-xs text-rose-600">{error}</p>}
            <button
              type="submit"
              disabled={sendOtpMutation.isPending}
              className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {sendOtpMutation.isPending ? 'Sending…' : 'Send reset code'}
            </button>
            <button
              type="button"
              onClick={() => navigate(ROUTE_PATHS.login)}
              className="w-full text-center text-xs text-text-secondary hover:text-text-primary transition-colors"
            >
              Back to sign in
            </button>
          </form>
        )}

        {step === 'otp' && (
          <form onSubmit={handleOtpSubmit} className="space-y-5">
            <div>
              <h1 className="text-xl font-bold text-text-primary">Enter reset code</h1>
              <p className="mt-1 text-sm text-text-secondary">
                We sent a 6-digit code to {phone}.
              </p>
            </div>
            {debugOtp ? <DevOtpCard otp={debugOtp} /> : null}
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">OTP code</label>
              <input
                type="text"
                placeholder="123456"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                maxLength={6}
                className="w-full rounded-lg border border-border bg-surface-secondary px-3 py-2.5 text-center text-xl font-mono font-semibold text-text-primary outline-none tracking-widest focus:border-indigo-500"
                required
              />
            </div>
            {error && <p className="text-xs text-rose-600">{error}</p>}
            <button
              type="submit"
              className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
            >
              Verify code
            </button>
          </form>
        )}

        {step === 'password' && (
          <form onSubmit={handlePasswordSubmit} className="space-y-5">
            <div>
              <h1 className="text-xl font-bold text-text-primary">New password</h1>
              <p className="mt-1 text-sm text-text-secondary">
                Choose a strong new password for your account.
              </p>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">New password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full rounded-lg border border-border bg-surface-secondary px-3 py-2.5 text-sm text-text-primary outline-none focus:border-indigo-500"
                required
                minLength={8}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Confirm password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-lg border border-border bg-surface-secondary px-3 py-2.5 text-sm text-text-primary outline-none focus:border-indigo-500"
                required
              />
            </div>
            {error && <p className="text-xs text-rose-600">{error}</p>}
            <button
              type="submit"
              disabled={confirmMutation.isPending}
              className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {confirmMutation.isPending ? 'Resetting…' : 'Reset password'}
            </button>
          </form>
        )}

        {step === 'done' && (
          <div className="space-y-5 text-center">
            <div className="flex flex-col items-center gap-3">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-3xl">
                ✓
              </div>
              <h1 className="text-xl font-bold text-text-primary">Password reset!</h1>
              <p className="text-sm text-text-secondary">
                Your password has been updated. You can now sign in.
              </p>
            </div>
            <button
              onClick={() => navigate(ROUTE_PATHS.login)}
              className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
            >
              Go to sign in
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
