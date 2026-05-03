export interface CameraService {
  scanQrCode(): Promise<{ value: string } | { error: 'not_implemented' }>
}
