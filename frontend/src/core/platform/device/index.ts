import type { DeviceIdentity } from './types'
import { WebDeviceIdentity } from './web-device-identity'

let deviceIdentity: DeviceIdentity = new WebDeviceIdentity()

export function getDeviceIdentity() {
  return deviceIdentity
}

export function setDeviceIdentity(adapter: DeviceIdentity) {
  deviceIdentity = adapter
}
