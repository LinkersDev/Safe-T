import { Link } from 'react-router-dom'
import { MobileScreenLayout } from '../../../shared/layouts/MobileScreenLayout'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import { ROUTE_PATHS } from '../../../app/routing/paths'
import { useAuthSession } from '../../../domains/security/hooks/useAuthSession'
import { isStaffRole } from '../../../core/permissions/capabilities'

export function ForbiddenPage() {
  const { user } = useAuthSession()
  const dashboardPath = isStaffRole(user?.role) ? ROUTE_PATHS.staff : ROUTE_PATHS.dashboard

  return (
    <MobileScreenLayout title="Access Restricted" subtitle="You do not have permission for this action.">
      <Card className="space-y-4">
        <p className="text-sm text-text-secondary">
          If this is unexpected, refresh your session or contact your administrator.
        </p>
        <Link to={dashboardPath}>
          <Button className="w-full">Back to dashboard</Button>
        </Link>
      </Card>
    </MobileScreenLayout>
  )
}
