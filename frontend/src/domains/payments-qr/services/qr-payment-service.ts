import QRCode from 'qrcode'
import { apiClient } from '../../../core/api/client'
import { isMockModeEnabled } from '../../../core/mock/mode'
import type {
  P2PReceiveQrIssueResponse,
  P2PReceiveQrIssueWithImage,
  P2PReceiveQrResolveResponse,
} from '../types'

export async function issueP2PReceiveQr(): Promise<P2PReceiveQrIssueResponse> {
  if (isMockModeEnabled()) {
    return {
      qr_payload: 'safet:p2p:v1:mock-signed-payload',
      expires_in_seconds: 3600,
    }
  }

  const response = await apiClient.post<P2PReceiveQrIssueResponse>(
    '/api/payments/p2p-receive-qr/issue/',
    {},
  )
  return response.data
}

export async function resolveP2PReceiveQrPayload(
  rawPayload: string,
): Promise<P2PReceiveQrResolveResponse> {
  const trimmed = rawPayload.trim()
  if (isMockModeEnabled()) {
    return {
      full_name: 'Mock Recipient',
      phone_number: '+252700000001',
      account_number: '6000000000000001',
      currency_code: 'USD',
    }
  }

  const response = await apiClient.get<P2PReceiveQrResolveResponse>(
    '/api/payments/p2p-receive-qr/resolve/',
    {
      params: { payload: trimmed },
    },
  )
  return response.data
}

export async function renderQrDataUrl(payload: string): Promise<string> {
  return QRCode.toDataURL(payload, {
    width: 240,
    margin: 1,
    errorCorrectionLevel: 'L',
  })
}

export async function issueP2PReceiveQrWithImage(): Promise<P2PReceiveQrIssueWithImage> {
  const issued: P2PReceiveQrIssueResponse = await issueP2PReceiveQr()
  const image_data_url = await renderQrDataUrl(issued.qr_payload)
  return { ...issued, image_data_url }
}
