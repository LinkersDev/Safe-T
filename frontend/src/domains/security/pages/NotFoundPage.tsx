import { Link } from 'react-router-dom'
import { MobileScreenLayout } from '../../../shared/layouts/MobileScreenLayout'
import { Button } from '../../../shared/components/ui/Button'
import { Card } from '../../../shared/components/ui/Card'
import { ROUTE_PATHS } from '../../../app/routing/paths'

export function NotFoundPage() {
  return (
    <MobileScreenLayout title="Page Not Found" subtitle="The requested route does not exist.">
      <Card>
        <Link to={ROUTE_PATHS.login}>
          <Button className="w-full">Go to login</Button>
        </Link>
      </Card>
    </MobileScreenLayout>
  )
}
