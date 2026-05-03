"""Staff-facing support URLs. Prefix: /api/staff/support/"""
from django.urls import path

from . import views

urlpatterns = [
    path("tickets/",                           views.staff_ticket_list,    name="staff-support-ticket-list"),
    path("tickets/<int:ticket_id>/",           views.staff_ticket_detail,  name="staff-support-ticket-detail"),
    path("tickets/<int:ticket_id>/reply/",     views.staff_ticket_reply,   name="staff-support-ticket-reply"),
    path("tickets/<int:ticket_id>/assign/",    views.staff_ticket_assign,  name="staff-support-ticket-assign"),
    path("tickets/<int:ticket_id>/resolve/",   views.staff_ticket_resolve, name="staff-support-ticket-resolve"),
    path("tickets/<int:ticket_id>/close/",     views.staff_ticket_close,   name="staff-support-ticket-close"),
]
