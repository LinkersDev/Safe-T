import { useEffect, useRef, useState, useCallback } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Html5Qrcode } from 'html5-qrcode'
import { useNavigate } from 'react-router-dom'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { normalizeApiError } from '../../../core/api/error-normalizer'
import { cn } from '../../../core/utils/cn'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import {
  issueP2PReceiveQrWithImage,
  resolveP2PReceiveQrPayload,
} from '../services/qr-payment-service'

type TabId = 'my' | 'scan'

export function QrPaymentPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [tab, setTab] = useState<TabId>('my')
  const [scanNonce, setScanNonce] = useState(0)
  const [scanError, setScanError] = useState<string | null>(null)
  const decodeHandledRef = useRef(false)
  const resolveMutateRef = useRef<(raw: string) => void>(() => {})
  const scannerRef = useRef<Html5Qrcode | null>(null)
  const scannerStartedRef = useRef(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const issueQuery = useQuery({
    queryKey: ['p2p-receive-qr-issue'],
    queryFn: issueP2PReceiveQrWithImage,
    enabled: tab === 'my',
    staleTime: 60_000,
  })

  const resolveMutation = useMutation({
    mutationFn: resolveP2PReceiveQrPayload,
    onSuccess: (data) => {
      setScanError(null)
      navigate(ROUTE_PATHS.transfer, {
        replace: false,
        state: {
          fromQrScan: true,
          destinationPhoneNumber: data.phone_number,
          destinationAccountNumber: data.account_number,
          recipientFullName: data.full_name,
        },
      })
    },
    onError: (err) => setScanError(normalizeApiError(err).detail),
  })

  resolveMutateRef.current = (raw: string) => resolveMutation.mutate(raw)

  useEffect(() => {
    if (tab !== 'scan') {
      decodeHandledRef.current = false
      return undefined
    }

    decodeHandledRef.current = false
    setScanError(null)

    const containerId = `p2p-qr-scanner-region-${scanNonce}`

    // Delay scanner init by a tick to ensure the container div is mounted.
    const startTimer = window.setTimeout(() => {
      let html5: Html5Qrcode
      try {
        html5 = new Html5Qrcode(containerId)
      } catch {
        setScanError('Camera scanner failed to initialize.')
        return
      }

      scannerRef.current = html5
      scannerStartedRef.current = false

      const onDecoded = (text: string) => {
        if (decodeHandledRef.current) return
        const trimmed = text.trim()
        if (!trimmed.startsWith('safet:p2p:v1:')) {
          setScanError('Not a valid SafeT peer QR code.')
          return
        }
        decodeHandledRef.current = true
        void html5
          .stop()
          .catch(() => {})
          .finally(() => {
            scannerStartedRef.current = false
            try {
              html5.clear()
            } catch {
              /* ignore */
            }
            resolveMutateRef.current(trimmed)
          })
      }

      const start = async () => {
        try {
          await html5.start(
            { facingMode: 'environment' },
            { fps: 10, qrbox: { width: 260, height: 260 } },
            onDecoded,
            () => {},
          )
          scannerStartedRef.current = true
          return
        } catch {
          // ignore and try next strategy
        }

        try {
          const cameras = await Html5Qrcode.getCameras()
          if (!cameras.length) throw new Error('no_cameras')
          await html5.start(
            { deviceId: cameras[0].id },
            { fps: 10, qrbox: { width: 260, height: 260 } },
            onDecoded,
            () => {},
          )
          scannerStartedRef.current = true
        } catch {
          setScanError(
            'Could not open the camera. Allow camera access and use HTTPS (or localhost).',
          )
        }
      }

      void start()
    }, 0)

    return () => {
      decodeHandledRef.current = true
      window.clearTimeout(startTimer)
      const html5 = scannerRef.current
      scannerRef.current = null

      if (!html5) return

      const stopPromise = scannerStartedRef.current ? html5.stop().catch(() => {}) : Promise.resolve()
      void stopPromise.finally(() => {
        scannerStartedRef.current = false
        try {
          html5.clear()
        } catch {
          /* ignore */
        }
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount scanner when tab/nonce changes only
  }, [tab, scanNonce])

  function refreshMyQr() {
    void qc.invalidateQueries({ queryKey: ['p2p-receive-qr-issue'] })
  }

  function restartCamera() {
    decodeHandledRef.current = false
    setScanError(null)
    setScanNonce((n) => n + 1)
  }

  const handleFileSelect = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    event.target.value = ''
    setScanError(null)
    try {
      const helper = new Html5Qrcode('p2p-qr-file-scan-helper')
      const decoded = await helper.scanFile(file, false)
      try { helper.clear() } catch { /* ignore */ }
      const trimmed = decoded.trim()
      if (!trimmed.startsWith('safet:p2p:v1:')) {
        setScanError('Not a valid SafeT peer QR code.')
        return
      }
      decodeHandledRef.current = true
      resolveMutateRef.current(trimmed)
    } catch {
      setScanError('Could not read a QR code from that image. Try a clearer photo.')
    }
  }, [])

  const scannerDomId = `p2p-qr-scanner-region-${scanNonce}`

  return (
    <div className="max-w-xl space-y-4">
      <div className="flex gap-2 rounded-xl border border-border bg-surface-secondary p-1">
        <button
          type="button"
          onClick={() => setTab('my')}
          className={cn(
            'flex-1 rounded-lg py-2 text-sm font-semibold transition-colors',
            tab === 'my'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-text-secondary hover:bg-surface-primary',
          )}
        >
          My QR
        </button>
        <button
          type="button"
          onClick={() => setTab('scan')}
          className={cn(
            'flex-1 rounded-lg py-2 text-sm font-semibold transition-colors',
            tab === 'scan'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-text-secondary hover:bg-surface-primary',
          )}
        >
          Scan QR
        </button>
      </div>

      {tab === 'my' ? (
        <Card className="space-y-4 text-center">
          <p className="text-sm text-text-secondary">
            Another customer can scan this code to pay you via Send Money. Codes expire in about{' '}
            {issueQuery.data?.expires_in_seconds
              ? Math.round(issueQuery.data.expires_in_seconds / 60)
              : 60}{' '}
            minutes.
          </p>
          {issueQuery.isLoading ? (
            <p className="text-sm text-text-tertiary">Generating QR…</p>
          ) : issueQuery.isError ? (
            <p className="text-sm text-brand-danger">Could not load your receive QR.</p>
          ) : issueQuery.data?.image_data_url ? (
            <div className="flex justify-center">
              <img
                src={issueQuery.data.image_data_url}
                alt="Receive payment QR"
                className="rounded-xl border border-border bg-white p-3"
              />
            </div>
          ) : null}
          <Button type="button" variant="secondary" className="w-full" onClick={refreshMyQr}>
            Refresh QR
          </Button>
        </Card>
      ) : (
        <Card className="space-y-3">
          <p className="text-sm text-text-secondary">
            Point the camera at the recipient&apos;s SafeT peer QR. After scanning, you&apos;ll go to{' '}
            <strong>Send Money</strong> with their phone and account filled in for you to verify.
          </p>
          <div
            id={scannerDomId}
            className="overflow-hidden rounded-xl border border-border bg-black [&_video]:mx-auto [&_video]:max-h-[min(320px,55vh)]"
          />
          <div id="p2p-qr-file-scan-helper" style={{ display: 'none' }} />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
          {resolveMutation.isPending ? (
            <p className="text-center text-sm text-text-tertiary">Confirming recipient…</p>
          ) : null}
          {scanError ? <p className="text-center text-sm text-brand-danger">{scanError}</p> : null}
          <Button type="button" variant="secondary" className="w-full" onClick={restartCamera}>
            Restart camera
          </Button>
          <Button type="button" variant="secondary" className="w-full" onClick={() => fileInputRef.current?.click()}>
            Use image instead
          </Button>
        </Card>
      )}
    </div>
  )
}
