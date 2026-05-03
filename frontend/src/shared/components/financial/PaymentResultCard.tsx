import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import type { Transaction } from '../../../domains/ledger/types'

type PaymentResultCardProps = {
  transaction: Transaction
}

export function PaymentResultCard({ transaction }: PaymentResultCardProps) {
  const isComplete = transaction.status === 'COMPLETED'

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-text-secondary">Payment result</span>
        <Badge variant={isComplete ? 'success' : 'warning'}>{transaction.status}</Badge>
      </div>
      <div className="text-2xl font-bold text-text-primary">
        {transaction.currency} {transaction.amount.toLocaleString()}
      </div>
      <div className="space-y-1 text-sm text-text-secondary">
        <p>{transaction.description}</p>
        <p className="font-mono text-xs text-text-tertiary">{transaction.reference}</p>
      </div>
    </Card>
  )
}
