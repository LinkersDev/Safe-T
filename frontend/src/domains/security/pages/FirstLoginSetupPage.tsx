import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { MobileScreenLayout } from '../../../shared/layouts/MobileScreenLayout'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import { Input } from '../../../shared/components/ui/Input'
import { DevOtpCard } from '../../../shared/components/ui/DevOtpCard'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { normalizeApiError } from '../../../core/api/error-normalizer'
import { startSession } from '../hooks/useAuthSession'
import { completeFirstLogin } from '../services/auth-service'

export function FirstLoginSetupPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = location.state as
    | { phoneNumber?: string; otpCode?: string; debugOtp?: string }
    | null

  const [password, setPassword] = useState('')
  const [pin, setPin] = useState('')
  const [error, setError] = useState<string | null>(null)

  if (!state?.phoneNumber || !state?.otpCode) {
    return <Navigate to={ROUTE_PATHS.login} replace />
  }

  const mutation = useMutation({
    mutationFn: () =>
      completeFirstLogin({
        phoneNumber: state.phoneNumber!,
        otpCode: state.otpCode!,
        password,
        pin,
      }),
    onSuccess: (resp) => {
      startSession(resp)
      navigate(ROUTE_PATHS.dashboard, { replace: true })
    },
    onError: (e) => {
      const normalized = normalizeApiError(e)
      setError(normalized.detail)
    },
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    mutation.mutate()
  }

  return (
    <MobileScreenLayout title="Set up your account" subtitle="Create your password and transaction PIN.">
      <Card as="form" className="space-y-4" onSubmit={onSubmit}>
        {state.debugOtp ? <DevOtpCard otp={state.debugOtp} /> : null}
        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary" htmlFor="password">
            New password
          </label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            hasError={Boolean(error)}
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary" htmlFor="pin">
            New PIN (4 digits)
          </label>
          <Input
            id="pin"
            inputMode="numeric"
            maxLength={4}
            placeholder="1234"
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 4))}
            required
            hasError={Boolean(error)}
          />
        </div>
        {error ? <p className="text-sm text-brand-danger">{error}</p> : null}
        <Button className="w-full" loading={mutation.isPending} type="submit">
          Complete setup
        </Button>
      </Card>
    </MobileScreenLayout>
  )
}

