import type { DeviceIdentity } from './types'
import { createLogger } from '../../utils/logger'

const logger = createLogger('WebDeviceIdentity')
const DEVICE_KEY = 'safet.device.id'

function generateDeviceId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  return `web-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export class WebDeviceIdentity implements DeviceIdentity {
  async getDeviceId(): Promise<string> {
    try {
      const cached = window.localStorage.getItem(DEVICE_KEY)
      if (cached) {
        return cached
      }

      const generated = generateDeviceId()
      window.localStorage.setItem(DEVICE_KEY, generated)
      logger.info('Generated new device ID')
      return generated
    } catch (error) {
      logger.error('Failed to get device ID', error)
      return generateDeviceId()
    }
  }

  async getDeviceName(): Promise<string> {
    return 'SafeT Web Client'
  }
}
