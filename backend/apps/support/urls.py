"""Customer-facing support URLs. Prefix: /api/support/"""
from django.urls import path

from . import views

urlpatterns = [
    # Tickets
    path("tickets/",                         views.ticket_list_create,       name="support-ticket-list"),
    path("tickets/<int:ticket_id>/",         views.ticket_detail,            name="support-ticket-detail"),
    path("tickets/<int:ticket_id>/reply/",   views.ticket_reply,             name="support-ticket-reply"),
    path("tickets/<int:ticket_id>/close/",   views.ticket_close,             name="support-ticket-close"),
    # Notifications
    path("notifications/",                                views.notification_list,         name="support-notif-list"),
    path("notifications/unread-count/",                   views.notification_unread_count, name="support-notif-count"),
    path("notifications/read-all/",                       views.notification_read_all,     name="support-notif-read-all"),
    path("notifications/<int:notification_id>/read/",     views.notification_read_one,     name="support-notif-read-one"),
]
