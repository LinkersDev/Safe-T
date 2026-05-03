"""Customer-facing KYC URLs. Prefix: /api/kyc/"""
from django.urls import path

from . import views

urlpatterns = [
    path("status/", views.kyc_status, name="kyc-status"),
    path("profile/", views.kyc_profile_get, name="kyc-profile-get"),
    path("profile/submit/", views.kyc_profile_submit, name="kyc-profile-submit"),
    path("upload/", views.kyc_upload, name="kyc-upload"),
]
