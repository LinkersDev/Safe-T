import type { NotificationService } from './types'
import { WebNotificationService } from './web-notification-service'

let notificationService: NotificationService = new WebNotificationService()

export function getNotificationService() {
  return notificationService
}

export function setNotificationService(service: NotificationService) {
  notificationService = service
}
