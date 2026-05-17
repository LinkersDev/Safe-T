import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ROUTE_PATHS } from '../../app/routing/paths'
import { subscribeSessionExpired } from '../../core/events/session-events'

export function SessionExpiredBanner() {
  const [visible, setVisible] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const unsubscribe = subscribeSessionExpired(() => setVisible(true))
    return () => { unsubscribe() }
  }, [])

  // Auto-dismiss once the user navigates away from the login page (successful sign-in)
  useEffect(() => {
    if (visible && location.pathname !== ROUTE_PATHS.login) {
      setVisible(false)
    }
  }, [location.pathname, visible])

  if (!visible) return null

  return (
    <div className="fixed inset-x-0 top-0 z-50 flex items-center justify-between gap-4 border-b border-amber-300 bg-amber-50 px-4 py-3">
      <p className="text-sm font-medium text-amber-800">
        Your session has expired. Please sign in again.
      </p>
      <button
        onClick={() => {
          setVisible(false)
          navigate(ROUTE_PATHS.login, { replace: true })
        }}
        className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-600 transition-colors"
      >
        Sign in
      </button>
    </div>
  )
}
