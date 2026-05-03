import type { CameraService } from './types'
import { WebCameraService } from './web-camera-service'

let cameraService: CameraService = new WebCameraService()

export function getCameraService() {
  return cameraService
}

export function setCameraService(service: CameraService) {
  cameraService = service
}
