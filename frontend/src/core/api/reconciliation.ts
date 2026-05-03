export function shouldReconcilePayment(status: number | null) {
  return status === 409 || status === 408 || status === 425 || (status !== null && status >= 500)
}

export function getReconciliationMessage(detail: string) {
  return `${detail} Check transaction history before retrying.`
}
