import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { AuthScreenLayout } from '../../../shared/layouts/AuthScreenLayout'
import { LogoAvatar } from '../../../shared/components/LogoAvatar'
import { Button } from '../../../shared/components/ui/Button'
import { Input } from '../../../shared/components/ui/Input'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { normalizeApiError } from '../../../core/api/error-normalizer'
import { startMockSession, startSession } from '../hooks/useAuthSession'
import { isAuthMockMode, loginWithCredentials, loginWithOtp, sendFirstLoginOtp, sendLoginOtp } from '../services/auth-service'

export function LoginPage() {
  const navigate = useNavigate()
  const [phoneNumber, setPhoneNumber] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [firstLoginRequired, setFirstLoginRequired] = useState(false)

  const loginMutation = useMutation({
    mutationFn: async () => {
      if (isAuthMockMode()) {
        return loginWithCredentials(phoneNumber, password)
      }
      return loginWithOtp({ phoneNumber, password })
    },
    onSuccess: (response) => {
      if (isAuthMockMode() && 'otp_required' in response) {
        if (response.otp_required) {
          setMessage('OTP required to continue login.')
          navigate(ROUTE_PATHS.otp, {
            state: {
              phoneNumber,
              password,
              mockAuth: response,
              debugOtp: '123456',
            },
          })
          return
        }
        startMockSession(response)
        navigate(ROUTE_PATHS.dashboard, { replace: true })
        setMessage(null)
        setError(null)
        return
      }

      // Real backend success — store JWT tokens and redirect by role
      if (!('access' in response)) return
      startSession(response as import('../types').LoginResponse)
      const staffRoles = ['ADMIN', 'TELLER', 'TELLER_ADMIN', 'CUSTOMER_SERVICE', 'RISK_OFFICER']
      const userRole = response.user?.role ?? ''
      navigate(staffRoles.includes(userRole) ? ROUTE_PATHS.staff : ROUTE_PATHS.dashboard, { replace: true })
      setMessage(null)
      setError(null)
      setFirstLoginRequired(false)
    },
    onError: (nextError) => {
      const normalized = normalizeApiError(nextError)
      setMessage(null)
      setError(normalized.detail)
      setFirstLoginRequired(normalized.code === 'first_login_required')

      if (normalized.code === 'otp_required') {
        sendLoginOtp(phoneNumber)
          .then((resp) => {
            setMessage('OTP required to continue login.')
            navigate(ROUTE_PATHS.otp, {
              state: { phoneNumber, password, debugOtp: resp.dev_otp ?? resp._debug_otp },
            })
          })
          .catch(() => setError('Could not send OTP. Check the phone number.'))
      }
    },
  })

  const firstLoginOtpMutation = useMutation({
    mutationFn: () => sendFirstLoginOtp(phoneNumber),
    onSuccess: (resp) => {
      navigate(ROUTE_PATHS.otp, {
        state: {
          phoneNumber,
          debugOtp: resp.dev_otp ?? resp._debug_otp,
          firstLogin: true,
        },
      })
    },
    onError: () => {
      setError('Could not send OTP for first login. Check the phone number.')
    },
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    loginMutation.mutate()
  }

  return (
    <AuthScreenLayout
      title="Welcome to SaFe-T"
      subtitle="Secure Login"
      logo={<LogoAvatar src="/logo.png" alt="SaFe-T Logo" />}
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary" htmlFor="phone">
            Phone number
          </label>
          <Input
            id="phone"
            name="phone"
            type="tel"
            autoComplete="tel"
            inputMode="tel"
            placeholder="+252XXXXXXXXX"
            value={phoneNumber}
            onChange={(event) => setPhoneNumber(event.target.value)}
            required
            hasError={Boolean(error)}
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary" htmlFor="password">
            Password
          </label>
          <div className="relative">
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              hasError={Boolean(error)}
              className="pr-12"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md px-2 py-1 text-xs font-medium text-text-secondary hover:text-text-primary"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>
        {error ? <p className="text-sm text-brand-danger">{error}</p> : null}
        {message ? <p className="text-sm text-brand-success">{message}</p> : null}
        <Button className="w-full" loading={loginMutation.isPending} type="submit">
          Sign in
        </Button>
        {firstLoginRequired && (
          <Button
            className="w-full"
            variant="secondary"
            type="button"
            loading={firstLoginOtpMutation.isPending}
            onClick={() => firstLoginOtpMutation.mutate()}
          >
            First-time setup (send OTP)
          </Button>
        )}
        {isAuthMockMode() ? (
          <p className="text-xs text-text-tertiary">
            Demo: +252611000000 / Admin1234! (Admin) · +252771000010 / Customer1234! (Customer)
          </p>
        ) : (
          <p className="text-xs text-text-tertiary">Use your registered phone number.</p>
        )}
        <div className="text-center">
          <button
            type="button"
            onClick={() => navigate(ROUTE_PATHS.resetPassword)}
            className="text-xs font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
          >
            Forgot password?
          </button>
        </div>
      </form>
    </AuthScreenLayout>
  )
}
