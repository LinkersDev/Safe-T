export interface NotificationService {
  requestPermission(): Promise<'granted' | 'denied' | 'not_implemented'>
}
