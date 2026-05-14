import type { ComponentType, LazyExoticComponent } from 'react'
import type { RoleCode } from '../../core/state/auth-state'

export type RouteMetadata = {
  path: string
  component: LazyExoticComponent<ComponentType<any>>
  /**
   * If true, this route is excluded from mobile builds for customers.
   * Staff can still access these routes on mobile if they log in.
   */
  mobileExclude?: boolean
  /**
   * If true, this route is only for customers (not staff).
   */
  customerOnly?: boolean
  /**
   * Required roles to access this route.
   */
  allowedRoles?: RoleCode[]
  /**
   * Required permission to access this route.
   */
  requiredPermission?: string
  /**
   * Route group for organization.
   */
  group?: 'auth' | 'customer' | 'staff' | 'teller' | 'risk' | 'error'
}

/**
 * Check if a route should be loaded based on platform and metadata.
 */
export function shouldLoadRoute(route: RouteMetadata, isMobile: boolean, userRole?: RoleCode | null): boolean {
  // Always load on web
  if (!isMobile) {
    return true
  }

  // On mobile, check if route is excluded for customers
  if (route.mobileExclude) {
    // If user is staff, load the route (staff can access on mobile)
    if (userRole && ['ADMIN', 'TELLER', 'TELLER_ADMIN', 'RISK_OFFICER', 'CUSTOMER_SERVICE'].includes(userRole)) {
      return true
    }
    // Otherwise, exclude this route on mobile
    return false
  }

  // Load all other routes
  return true
}
