import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { cn } from '../../../core/utils/cn'

type ToastVariant = 'success' | 'error' | 'info' | 'warning'

type Toast = {
  id: string
  message: string
  variant: ToastVariant
}

type ToastContextValue = {
  showToast: (message: string, variant?: ToastVariant) => void
  success: (message: string) => void
  error: (message: string) => void
  warning: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showToast = useCallback((message: string, variant: ToastVariant = 'info') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((prev) => [...prev, { id, message, variant }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider
      value={{
        showToast,
        success: (m) => showToast(m, 'success'),
        error: (m) => showToast(m, 'error'),
        warning: (m) => showToast(m, 'warning'),
        info: (m) => showToast(m, 'info'),
      }}
    >
      {children}
      {/* Toast stack */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 min-w-72 max-w-sm">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={cn(
              'flex items-start justify-between gap-3 rounded-xl border px-4 py-3 shadow-md text-sm font-medium',
              toast.variant === 'success' && 'bg-emerald-50 border-emerald-200 text-emerald-800',
              toast.variant === 'error'   && 'bg-rose-50   border-rose-200   text-rose-800',
              toast.variant === 'warning' && 'bg-amber-50  border-amber-200  text-amber-800',
              toast.variant === 'info'    && 'bg-blue-50   border-blue-200   text-blue-800',
            )}
          >
            <span>{toast.message}</span>
            <button
              onClick={() => dismiss(toast.id)}
              className="ml-2 text-current opacity-50 hover:opacity-100 leading-none"
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
