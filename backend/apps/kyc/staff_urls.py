"""Staff-facing KYC URLs. Prefix: /api/staff/kyc/"""
from django.urls import path

from . import views

urlpatterns = [
    path("pending/",                              views.staff_kyc_pending,         name="kyc-staff-pending"),
    path("users/<int:user_id>/documents/",        views.staff_user_documents,      name="kyc-staff-user-docs"),
    path("users/<int:user_id>/approve/",          views.staff_approve_user_kyc,    name="kyc-staff-approve-user"),
    path("users/<int:user_id>/reject/",           views.staff_reject_user_kyc,     name="kyc-staff-reject-user"),
    path("documents/<int:doc_id>/approve/",       views.staff_approve_document,    name="kyc-staff-approve-doc"),
    path("documents/<int:doc_id>/reject/",        views.staff_reject_document,     name="kyc-staff-reject-doc"),
]
