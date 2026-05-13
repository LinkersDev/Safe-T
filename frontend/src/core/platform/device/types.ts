export interface DeviceIdentity {
  getDeviceId(): Promise<string>
  getDeviceName(): Promise<string>
}
