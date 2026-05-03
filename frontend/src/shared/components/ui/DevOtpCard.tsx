import { useMemo, useState } from 'react'
import { Button } from './Button'

type DevOtpCardProps = {
  otp: string
  className?: string
}

async function copyText(text: string) {
  if (navigator?.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'true')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '0'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

export function DevOtpCard({ otp, className }: DevOtpCardProps) {
  const [status, setStatus] = useState<'idle' | 'copied' | 'failed'>('idle')

  const label = useMemo(() => {
    if (status === 'copied') return 'Copied'
    if (status === 'failed') return 'Copy failed'
    return 'Copy'
  }, [status])

  async function handleCopy() {
    try {
      await copyText(otp)
      setStatus('copied')
      window.setTimeout(() => setStatus('idle'), 1200)
    } catch {
      setStatus('failed')
      window.setTimeout(() => setStatus('idle'), 1500)
    }
  }

  return (
    <div className={['rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800', className].filter(Boolean).join(' ')}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold">DEV ONLY OTP</p>
          <p className="mt-0.5 font-mono text-base tracking-widest">{otp}</p>
        </div>
        <Button
          className="min-h-[36px] px-3 py-1.5 text-xs"
          type="button"
          variant="secondary"
          onClick={handleCopy}
        >
          {label}
        </Button>
      </div>
    </div>
  )
}

