import { hasPermission } from '../../../core/permissions/capabilities'
import { useAuthSession } from '../../../domains/security/hooks/useAuthSession'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import type { ReactNode } from 'react'

type PermissionGuardProps = {
  requiredPermission: string
  children: ReactNode
}

export function PermissionGuard({ requiredPermission, children }: PermissionGuardProps) {
  useAuthSession()

  if (!hasPermission(requiredPermission)) {
    return (
      <div className="p-4 sm:p-6">
        <StatusNoticeCard
          title="Access restricted"
          message={`Missing permission: ${requiredPermission}. Contact an administrator to request access.`}
          variant="warning"
        />
      </div>
    )
  }

  return <>{children}</>
}
