import { Device } from '@capacitor/device';
import { Preferences } from '@capacitor/preferences';
import type { DeviceIdentity } from './types';
import { createLogger } from '../../utils/logger';

const logger = createLogger('CapacitorDeviceIdentity');

const DEVICE_UUID_KEY = 'safet.device.persistent.uuid';

function generatePersistentUUID(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export class CapacitorDeviceIdentity implements DeviceIdentity {
  private cachedId: string | null = null;
  private cachedName: string | null = null;

  async getDeviceId(): Promise<string> {
    if (this.cachedId) return this.cachedId;
    
    try {
      const { value: persistentUUID } = await Preferences.get({ key: DEVICE_UUID_KEY });
      
      if (persistentUUID) {
        this.cachedId = persistentUUID;
        return persistentUUID;
      }
      
      const newUUID = generatePersistentUUID();
      await Preferences.set({ key: DEVICE_UUID_KEY, value: newUUID });
      this.cachedId = newUUID;
      logger.info('Generated new persistent UUID');
      return newUUID;
      
    } catch (error) {
      logger.error('Failed to get persistent UUID', error);
      try {
        const info = await Device.getId();
        this.cachedId = info.identifier || generatePersistentUUID();
        return this.cachedId;
      } catch {
        return generatePersistentUUID();
      }
    }
  }

  async getDeviceName(): Promise<string> {
    if (this.cachedName) return this.cachedName;
    
    try {
      const info = await Device.getInfo();
      this.cachedName = `${info.manufacturer} ${info.model}`.trim() || 'SafeT Mobile';
      return this.cachedName;
    } catch (error) {
      logger.error('Failed to get device name', error);
      return 'SafeT Mobile';
    }
  }
}
