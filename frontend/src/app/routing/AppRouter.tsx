import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { ROUTE_PATHS } from './paths'
import { AuthGuard } from './guards/AuthGuard'
import { PermissionGuard } from './guards/PermissionGuard'
import { RoleGuard } from './guards/RoleGuard'
import { AppShell } from '../../shared/layouts/AppShell'
import type { RoleCode } from '../../core/state/auth-state'
import type { ReactNode } from 'react'

const STAFF_ROLES: RoleCode[] = ['ADMIN', 'TELLER', 'TELLER_ADMIN', 'CUSTOMER_SERVICE', 'RISK_OFFICER']
const CUSTOMER_ROLES: RoleCode[] = ['CUSTOMER', 'MERCHANT_CUSTOMER']

const LoginPage       = lazy(() => import('../../domains/security/pages/LoginPage').then(m => ({ default: m.LoginPage })))
const OtpPage         = lazy(() => import('../../domains/security/pages/OtpPage').then(m => ({ default: m.OtpPage })))
const FirstLoginSetupPage = lazy(() => import('../../domains/security/pages/FirstLoginSetupPage').then(m => ({ default: m.FirstLoginSetupPage })))
const PasswordResetPage = lazy(() => import('../../domains/security/pages/PasswordResetPage').then(m => ({ default: m.PasswordResetPage })))
const DashboardPage   = lazy(() => import('../../domains/accounts/pages/DashboardPage').then(m => ({ default: m.DashboardPage })))
const TransactionHistoryPage = lazy(() => import('../../domains/ledger/pages/TransactionHistoryPage').then(m => ({ default: m.TransactionHistoryPage })))
const TransactionDetailPage  = lazy(() => import('../../domains/ledger/pages/TransactionDetailPage').then(m => ({ default: m.TransactionDetailPage })))
const ProfilePage     = lazy(() => import('../../domains/security/pages/ProfilePage').then(m => ({ default: m.ProfilePage })))
const TransferPage    = lazy(() => import('../../domains/payments-transfer/pages/TransferPage').then(m => ({ default: m.TransferPage })))
const QrPaymentPage   = lazy(() => import('../../domains/payments-qr/pages/QrPaymentPage').then(m => ({ default: m.QrPaymentPage })))
const BillPaymentPage = lazy(() => import('../../domains/payments-bills/pages/BillPaymentPage').then(m => ({ default: m.BillPaymentPage })))
const TicketsPage     = lazy(() => import('../../domains/support/pages/TicketsPage').then(m => ({ default: m.TicketsPage })))
const TicketDetailPage = lazy(() => import('../../domains/support/pages/TicketDetailPage').then(m => ({ default: m.TicketDetailPage })))
const NotificationsPage = lazy(() => import('../../domains/support/pages/NotificationsPage').then(m => ({ default: m.NotificationsPage })))
const StaffDashboardPage = lazy(() => import('../../domains/staff/pages/StaffDashboardPage').then(m => ({ default: m.StaffDashboardPage })))
const StaffUsersPage  = lazy(() => import('../../domains/staff-users/pages/StaffUsersPage').then(m => ({ default: m.StaffUsersPage })))
const StaffRegisterStaffPage = lazy(() => import('../../domains/staff-users/pages/StaffRegisterStaffPage').then(m => ({ default: m.StaffRegisterStaffPage })))
const StaffKycPage    = lazy(() => import('../../domains/staff-kyc/pages/StaffKycPage').then(m => ({ default: m.StaffKycPage })))
const StaffAccountsPage = lazy(() => import('../../domains/staff-accounts/pages/StaffAccountsPage').then(m => ({ default: m.StaffAccountsPage })))
const StaffLedgerPage = lazy(() => import('../../domains/staff-ledger/pages/StaffLedgerPage').then(m => ({ default: m.StaffLedgerPage })))
const StaffSupportPage = lazy(() => import('../../domains/staff-support/pages/StaffSupportPage').then(m => ({ default: m.StaffSupportPage })))
const StaffTicketDetailPage = lazy(() => import('../../domains/staff-support/pages/StaffTicketDetailPage').then(m => ({ default: m.StaffTicketDetailPage })))
const RiskAlertsPage  = lazy(() => import('../../domains/risk/pages/RiskAlertsPage').then(m => ({ default: m.RiskAlertsPage })))
const StaffReportsPage = lazy(() => import('../../domains/staff-reporting/pages/StaffReportsPage').then(m => ({ default: m.StaffReportsPage })))
const TellerRegisterCustomerPage = lazy(() => import('../../domains/teller/pages/TellerRegisterCustomerPage').then(m => ({ default: m.TellerRegisterCustomerPage })))
const TellerDepositPage = lazy(() => import('../../domains/teller/pages/TellerDepositPage').then(m => ({ default: m.TellerDepositPage })))
const TellerWithdrawPage = lazy(() => import('../../domains/teller/pages/TellerWithdrawPage').then(m => ({ default: m.TellerWithdrawPage })))
const TellerAccountTransactionsPage = lazy(() => import('../../domains/teller/pages/TellerAccountTransactionsPage').then(m => ({ default: m.TellerAccountTransactionsPage })))
const TellerCustomerProfilePage = lazy(() => import('../../domains/teller/pages/TellerCustomerProfilePage').then(m => ({ default: m.TellerCustomerProfilePage })))
const TellerCustomerLookupPage = lazy(() => import('../../domains/teller/pages/TellerCustomerLookupPage').then(m => ({ default: m.TellerCustomerLookupPage })))
const ForbiddenPage   = lazy(() => import('../../domains/security/pages/ForbiddenPage').then(m => ({ default: m.ForbiddenPage })))
const NotFoundPage    = lazy(() => import('../../domains/security/pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })))

function RouteFallback() {
  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <div className="h-8 w-1/3 animate-pulse rounded-lg bg-surface-secondary" />
      <div className="h-32 w-full animate-pulse rounded-xl bg-surface-secondary" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1,2,3,4].map(i => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-surface-secondary" />
        ))}
      </div>
    </div>
  )
}

// Page title map — pattern paths need special handling
const PAGE_TITLES: Record<string, string> = {
  [ROUTE_PATHS.dashboard]:           'My Account',
  [ROUTE_PATHS.ledger]:              'Transaction History',
  [ROUTE_PATHS.transactionDetailPattern]: 'Transaction Receipt',
  [ROUTE_PATHS.profile]:             'My Profile',
  [ROUTE_PATHS.transfer]:            'Send Money',
  [ROUTE_PATHS.qrPayment]:           'QR Payment',
  [ROUTE_PATHS.billPayment]:         'Pay Bills',
  [ROUTE_PATHS.tickets]:             'Support Tickets',
  [ROUTE_PATHS.ticketDetailPattern]: 'Ticket Details',
  [ROUTE_PATHS.notifications]:       'Notifications',
  [ROUTE_PATHS.firstLoginSetup]:     'First Login Setup',
  [ROUTE_PATHS.staff]:               'Overview',
  [ROUTE_PATHS.staffUsers]:          'User Management',
  [ROUTE_PATHS.staffRegisterStaff]: 'Register Staff',
  [ROUTE_PATHS.staffKyc]:            'KYC Review Queue',
  [ROUTE_PATHS.staffAccounts]:       'Account Management',
  [ROUTE_PATHS.staffLedger]:         'Transaction Ledger',
  [ROUTE_PATHS.staffSupport]:        'Support Management',
  [ROUTE_PATHS.staffTicketDetailPattern]: 'Ticket Detail',
  [ROUTE_PATHS.staffRisk]:           'Risk Alerts',
  [ROUTE_PATHS.staffReports]:        'Reports & Analytics',
  [ROUTE_PATHS.staffTellerRegisterCustomer]: 'Register Customer',
  [ROUTE_PATHS.staffTellerDeposit]:          'Deposit',
  [ROUTE_PATHS.staffTellerWithdraw]:         'Withdraw',
  [ROUTE_PATHS.staffTellerAccountTransactions]: 'Account Transactions',
  [ROUTE_PATHS.staffTellerCustomerLookup]: 'Customer Lookup',
  [ROUTE_PATHS.staffTellerCustomerProfilePattern]: 'Customer Profile',
}

function Shell({ children }: { children: ReactNode }) {
  const location = useLocation()
  // Try exact match first, then check pattern matches for dynamic routes
  const title =
    PAGE_TITLES[location.pathname] ??
    (location.pathname.startsWith('/ledger/') ? 'Transaction Receipt' :
     location.pathname.startsWith('/staff/support/tickets/') ? 'Ticket Detail' :
     location.pathname.startsWith('/support/tickets/') ? 'Ticket Details' :
     location.pathname.startsWith('/staff/teller/customers/') ? 'Customer Profile' :
     'SafeT')
  return <AppShell title={title}>{children}</AppShell>
}

function withPaymentAccess(children: ReactNode) {
  return (
    <AuthGuard>
      <Shell>
        <RoleGuard allowedRoles={CUSTOMER_ROLES}>{children}</RoleGuard>
      </Shell>
    </AuthGuard>
  )
}

function withCustomerAccess(children: ReactNode) {
  return <AuthGuard><Shell><RoleGuard allowedRoles={CUSTOMER_ROLES}>{children}</RoleGuard></Shell></AuthGuard>
}

function withStaffAccess(children: ReactNode, requiredPermission?: string) {
  const guarded = requiredPermission ? (
    <PermissionGuard requiredPermission={requiredPermission}>{children}</PermissionGuard>
  ) : children

  return <AuthGuard><Shell><RoleGuard allowedRoles={STAFF_ROLES}>{guarded}</RoleGuard></Shell></AuthGuard>
}

export function AppRouter() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path={ROUTE_PATHS.root}                     element={<Navigate to={ROUTE_PATHS.login} replace />} />
        <Route path={ROUTE_PATHS.login}                    element={<LoginPage />} />
        <Route path={ROUTE_PATHS.otp}                      element={<OtpPage />} />
        <Route path={ROUTE_PATHS.firstLoginSetup}          element={<FirstLoginSetupPage />} />
        <Route path={ROUTE_PATHS.resetPassword}            element={<PasswordResetPage />} />
        <Route path={ROUTE_PATHS.dashboard}                element={withCustomerAccess(<DashboardPage />)} />
        <Route path={ROUTE_PATHS.kyc}                      element={withCustomerAccess(<Navigate to={ROUTE_PATHS.profile} replace />)} />
        <Route path={ROUTE_PATHS.ledger}                   element={withCustomerAccess(<TransactionHistoryPage />)} />
        <Route path={ROUTE_PATHS.transactionDetailPattern} element={withCustomerAccess(<TransactionDetailPage />)} />
        <Route path={ROUTE_PATHS.profile}                  element={withCustomerAccess(<ProfilePage />)} />
        <Route path={ROUTE_PATHS.transfer}                 element={withPaymentAccess(<TransferPage />)} />
        <Route path={ROUTE_PATHS.qrPayment}                element={withPaymentAccess(<QrPaymentPage />)} />
        <Route path={ROUTE_PATHS.billPayment}              element={withPaymentAccess(<BillPaymentPage />)} />
        <Route path={ROUTE_PATHS.tickets}                  element={withCustomerAccess(<TicketsPage />)} />
        <Route path={ROUTE_PATHS.ticketDetailPattern}      element={withCustomerAccess(<TicketDetailPage />)} />
        <Route path={ROUTE_PATHS.notifications}            element={withCustomerAccess(<NotificationsPage />)} />
        <Route path={ROUTE_PATHS.staff}                    element={withStaffAccess(<StaffDashboardPage />)} />
        <Route path={ROUTE_PATHS.staffUsers}               element={withStaffAccess(<StaffUsersPage />, 'view_all_users')} />
        <Route path={ROUTE_PATHS.staffRegisterStaff}       element={withStaffAccess(<StaffRegisterStaffPage />, 'view_all_users')} />
        <Route path={ROUTE_PATHS.staffKyc}                 element={withStaffAccess(<StaffKycPage />, 'review_kyc')} />
        <Route path={ROUTE_PATHS.staffAccounts}            element={withStaffAccess(<StaffAccountsPage />, 'view_all_accounts')} />
        <Route path={ROUTE_PATHS.staffLedger}              element={withStaffAccess(<StaffLedgerPage />, 'view_all_transactions')} />
        <Route path={ROUTE_PATHS.staffSupport}             element={withStaffAccess(<StaffSupportPage />, 'manage_support_tickets')} />
        <Route path={ROUTE_PATHS.staffTicketDetailPattern} element={withStaffAccess(<StaffTicketDetailPage />, 'manage_support_tickets')} />
        <Route path={ROUTE_PATHS.staffRisk}                element={withStaffAccess(<RiskAlertsPage />, 'review_fraud_alert')} />
        <Route path={ROUTE_PATHS.staffReports}             element={withStaffAccess(<StaffReportsPage />, 'view_all_transactions')} />
        <Route path={ROUTE_PATHS.staffTellerRegisterCustomer} element={withStaffAccess(<TellerRegisterCustomerPage />, 'staff_register_customer')} />
        <Route path={ROUTE_PATHS.staffTellerDeposit}          element={withStaffAccess(<TellerDepositPage />, 'staff_deposit')} />
        <Route path={ROUTE_PATHS.staffTellerWithdraw}         element={withStaffAccess(<TellerWithdrawPage />, 'staff_withdraw')} />
        <Route path={ROUTE_PATHS.staffTellerAccountTransactions} element={withStaffAccess(<TellerAccountTransactionsPage />, 'staff_view_account_transactions')} />
        <Route path={ROUTE_PATHS.staffTellerCustomerLookup} element={withStaffAccess(<TellerCustomerLookupPage />, 'review_kyc')} />
        <Route path={ROUTE_PATHS.staffTellerCustomerProfilePattern} element={withStaffAccess(<TellerCustomerProfilePage />, 'review_kyc')} />
        <Route path={ROUTE_PATHS.forbidden}                element={<ForbiddenPage />} />
        <Route path={ROUTE_PATHS.notFound}                 element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
