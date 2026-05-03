"""
Root URL configuration.
Each app registers its own urls.py; this file only aggregates them.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth + user management
    path("api/auth/", include("apps.security.urls")),
    path("api/users/", include("apps.users.urls")),
    # Core banking
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/ledger/", include("apps.ledger.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/merchant/", include("apps.payments.merchant_urls")),
    # Support & notifications
    path("api/support/", include("apps.support.urls")),
    # Customer KYC
    path("api/kyc/", include("apps.kyc.urls")),
    # Staff namespaces
    path("api/staff/", include("apps.users.staff_urls")),
    path("api/staff/teller/", include("apps.users.teller_urls")),
    path("api/staff/kyc/", include("apps.kyc.staff_urls")),
    path("api/staff/accounts/", include("apps.accounts.staff_urls")),
    path("api/staff/ledger/", include("apps.ledger.staff_urls")),
    path("api/staff/support/", include("apps.support.staff_urls")),
    path("api/staff/risk/", include("apps.risk.urls")),
    # Reporting & dashboards
    path("api/staff/reports/", include("apps.reporting.urls")),
]

# Serve user-uploaded media (KYC docs, etc.) in development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
