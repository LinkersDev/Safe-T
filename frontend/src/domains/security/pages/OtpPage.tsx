import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { MobileScreenLayout } from '../../../shared/layouts/MobileScreenLayout'
import { Badge } from '../../../shared/components/ui/Badge'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import { DevOtpCard } from '../../../shared/components/ui/DevOtpCard'
import { Input } from '../../../shared/components/ui/Input'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { normalizeApiError } from '../../../core/api/error-normalizer'
import { startMockSession, startSession } from '../hooks/useAuthSession'
import { isAuthMockMode, loginWithOtp, sendLoginOtp, sendFirstLoginOtp } from '../services/auth-service'
import type { LoginResponse, MockAuthLoginResponse } from '../types'

export function OtpPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = location.state as
    | {
        phoneNumber?: string
        password?: string
        debugOtp?: string
        mockAuth?: MockAuthLoginResponse
        firstLogin?: boolean
      }
    | null
  const [otpCode, setOtpCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [timer, setTimer] = useState(30)
  const [canResend, setCanResend] = useState(false)

  // Countdown timer effect
  useEffect(() => {
    if (timer <= 0) {
      setCanResend(true)
      return
    }
    const interval = setInterval(() => {
      setTimer((prev) => {
        if (prev <= 1) {
          clearInterval(interval)
          setCanResend(true)
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [timer])

  const resetTimer = useCallback(() => {
    setTimer(30)
    setCanResend(false)
    setError(null)
  }, [])

  const resendMutation = useMutation({
    mutationFn: async () => {
      if (state?.firstLogin) {
        const response = await sendFirstLoginOtp(phoneNumber)
        return response
      }
      const response = await sendLoginOtp(phoneNumber)
      return response
    },
    onSuccess: (response) => {
      resetTimer()
      // Update debug OTP if available
      if (response.dev_otp || response._debug_otp) {
        navigate(location.pathname, {
          replace: true,
          state: {
            ...state,
            debugOtp: response.dev_otp ?? response._debug_otp,
          },
        })
      }
    },
    onError: (nextError) => {
      const normalized = normalizeApiError(nextError)
      setError(normalized.detail || 'Failed to resend OTP. Please try again.')
    },
  })

  const loginMutation = useMutation({
    mutationFn: async () => {
      if (isAuthMockMode()) {
        if (!state?.mockAuth) {
          throw new Error('Mock auth session is missing. Restart login.')
        }
        if (otpCode !== '123456') {
          throw new Error('Invalid OTP code.')
        }
        return state.mockAuth
      }

      if (state?.firstLogin) {
        // We only verify OTP here; password+PIN is set on the next screen.
        // For simplicity, we keep OTP capture here and pass it forward.
        return { otp_verified: true }
      }

      return loginWithOtp({ phoneNumber: phoneNumber, password: state?.password, otpCode })
    },
    onSuccess: (response) => {
      if (state?.firstLogin) {
        navigate(ROUTE_PATHS.firstLoginSetup, { replace: true, state: { phoneNumber, otpCode, debugOtp: state.debugOtp } })
        return
      }
      if (isAuthMockMode() && state?.mockAuth) {
        startMockSession(response as MockAuthLoginResponse)
      } else {
        startSession(response as LoginResponse)
      }
      navigate(ROUTE_PATHS.dashboard, { replace: true })
    },
    onError: (nextError) => {
      if (nextError instanceof Error && nextError.message) {
        setError(nextError.message)
        return
      }

      const normalized = normalizeApiError(nextError)
      setError(normalized.detail)
    },
  })

  if (!state?.phoneNumber) {
    return <Navigate to={ROUTE_PATHS.login} replace />
  }

  const phoneNumber = state.phoneNumber

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    loginMutation.mutate()
  }

  return (
    <MobileScreenLayout title="OTP Verification" subtitle="Enter the one-time code sent to your phone.">
      <Card as="form" className="space-y-4" onSubmit={handleSubmit}>
        <Badge variant="info">6-digit code required</Badge>
        {state.debugOtp ? <DevOtpCard otp={state.debugOtp} /> : null}
        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary" htmlFor="otp">
            OTP code
          </label>
          <Input
            id="otp"
            inputMode="numeric"
            maxLength={6}
            placeholder="123456"
            value={otpCode}
            onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
            required
            hasError={Boolean(error)}
          />
        </div>
        {error ? <p className="text-sm text-brand-danger">{error}</p> : null}
        <Button className="w-full" loading={loginMutation.isPending} type="submit">
          {state?.firstLogin ? 'Continue' : 'Verify OTP'}
        </Button>
        <div className="flex items-center justify-center">
          {canResend ? (
            <Button
              variant="secondary"
              type="button"
              loading={resendMutation.isPending}
              onClick={() => resendMutation.mutate()}
              className="text-sm text-text-secondary hover:text-brand-primary bg-transparent"
            >
              Resend OTP
            </Button>
          ) : (
            <span className="text-sm text-text-tertiary">
              Resend OTP in {timer}s
            </span>
          )}
        </div>
      </Card>
    </MobileScreenLayout>
  )
}
