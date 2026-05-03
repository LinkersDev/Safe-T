import { Link } from 'react-router-dom'
import { MobileScreenLayout } from '../../../shared/layouts/MobileScreenLayout'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import { ROUTE_PATHS } from '../../../app/routing/paths'

export function ForbiddenPage() {
  return (
    <MobileScreenLayout title="Access Restricted" subtitle="You do not have permission for this action.">
      <Card className="space-y-4">
        <p className="text-sm text-text-secondary">
          If this is unexpected, refresh your session or contact your administrator.
        </p>
        <Link to={ROUTE_PATHS.dashboard}>
          <Button className="w-full">Back to dashboard</Button>
        </Link>
      </Card>
    </MobileScreenLayout>
  )
}
