const listeners = new Set<() => void>()

export function emitSessionExpired() {
  listeners.forEach((fn) => fn())
}

export function subscribeSessionExpired(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
