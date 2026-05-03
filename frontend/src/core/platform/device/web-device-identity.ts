import type { DeviceIdentity } from './types'

const DEVICE_KEY = 'safet.device.id'

function generateDeviceId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  return `web-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export class WebDeviceIdentity implements DeviceIdentity {
  getDeviceId() {
    const cached = window.localStorage.getItem(DEVICE_KEY)
    if (cached) {
      return cached
    }

    const generated = generateDeviceId()
    window.localStorage.setItem(DEVICE_KEY, generated)
    return generated
  }

  getDeviceName() {
    return 'SafeT Web Client'
  }
}
