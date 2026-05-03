import type { NotificationService } from './types'

export class WebNotificationService implements NotificationService {
  async requestPermission() {
    return 'not_implemented' as const
  }
}
