export function isMockModeEnabled() {
  return import.meta.env.VITE_DEV_MOCK_MODE === 'true'
}
