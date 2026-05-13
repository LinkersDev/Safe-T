import { Preferences } from '@capacitor/preferences';
import type { AuthTokens, TokenStorage } from './types';
import { createLogger } from '../../utils/logger';

const logger = createLogger('CapacitorTokenStorage');

const ACCESS_KEY = 'safet.access.token';
const REFRESH_KEY = 'safet.refresh.token';

export class CapacitorTokenStorage implements TokenStorage {
  async readAccessToken(): Promise<string | null> {
    try {
      const { value } = await Preferences.get({ key: ACCESS_KEY });
      return value;
    } catch (error) {
      logger.error('Failed to read access token', error);
      return null;
    }
  }

  async readRefreshToken(): Promise<string | null> {
    try {
      const { value } = await Preferences.get({ key: REFRESH_KEY });
      return value;
    } catch (error) {
      logger.error('Failed to read refresh token', error);
      return null;
    }
  }

  async saveTokens(tokens: AuthTokens): Promise<void> {
    try {
      await Promise.all([
        Preferences.set({ key: ACCESS_KEY, value: tokens.accessToken }),
        Preferences.set({ key: REFRESH_KEY, value: tokens.refreshToken })
      ]);
      logger.info('Tokens saved');
    } catch (error) {
      logger.error('Failed to save tokens', error);
      throw error;
    }
  }

  async clearTokens(): Promise<void> {
    try {
      await Promise.all([
        Preferences.remove({ key: ACCESS_KEY }),
        Preferences.remove({ key: REFRESH_KEY })
      ]);
      logger.info('Tokens cleared');
    } catch (error) {
      logger.error('Failed to clear tokens', error);
      throw error;
    }
  }
}
