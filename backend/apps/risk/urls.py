"""Risk Officer URLs.  Prefix: /api/staff/risk/"""
from django.urls import path

from . import views

urlpatterns = [
    path("alerts/",                        views.alert_list,    name="risk-alert-list"),
    path("alerts/<int:alert_id>/",         views.alert_detail,  name="risk-alert-detail"),
    path("alerts/<int:alert_id>/review/",  views.alert_review,  name="risk-alert-review"),
    path("alerts/<int:alert_id>/dismiss/", views.alert_dismiss, name="risk-alert-dismiss"),
]
