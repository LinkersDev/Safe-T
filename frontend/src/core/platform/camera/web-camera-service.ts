import type { CameraService } from './types'

export class WebCameraService implements CameraService {
  async scanQrCode() {
    return { error: 'not_implemented' as const }
  }
}
