import { Capacitor } from '@capacitor/core';

export type Platform = 'web' | 'android' | 'ios';

export function getPlatform(): Platform {
  if (!Capacitor.isNativePlatform()) {
    return 'web';
  }
  
  const platform = Capacitor.getPlatform();
  if (platform === 'android') return 'android';
  if (platform === 'ios') return 'ios';
  
  return 'web';
}

export function isWeb(): boolean {
  return getPlatform() === 'web';
}

export function isMobile(): boolean {
  return !isWeb();
}

export function isAndroid(): boolean {
  return getPlatform() === 'android';
}

export function isIOS(): boolean {
  return getPlatform() === 'ios';
}

/**
 * Check if we should load staff routes.
 * On mobile, staff routes are deferred until needed.
 * On web, all routes are always available.
 */
export function shouldLoadStaffRoutes(): boolean {
  // Always load staff routes on web
  if (isWeb()) {
    return true;
  }
  
  // On mobile, defer staff routes (load on-demand)
  return false;
}
