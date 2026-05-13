import type { DeviceIdentity } from './types'
import { WebDeviceIdentity } from './web-device-identity'
import { CapacitorDeviceIdentity } from './capacitor-device-identity'
import { isMobile } from '../platform-detector'

let deviceIdentity: DeviceIdentity = isMobile()
  ? new CapacitorDeviceIdentity()
  : new WebDeviceIdentity()

export function getDeviceIdentity(): DeviceIdentity {
  return deviceIdentity
}

export function setDeviceIdentity(identity: DeviceIdentity): void {
  deviceIdentity = identity
}
