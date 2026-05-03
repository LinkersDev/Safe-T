from django.contrib import admin

from .models import Notification, SupportTicket, SupportTicketMessage


class SupportTicketMessageInline(admin.TabularInline):
    model = SupportTicketMessage
    extra = 0
    readonly_fields = ("sender", "body", "is_internal", "created_at")
    can_delete = False


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display  = ("id", "user", "subject", "category", "status", "assigned_to", "created_at")
    list_filter   = ("status", "category")
    search_fields = ("subject", "user__phone_number", "user__full_name")
    readonly_fields = ("created_at", "updated_at", "resolved_at", "closed_at")
    inlines       = [SupportTicketMessageInline]
    ordering      = ("-created_at",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ("id", "user", "notification_type", "title", "is_read", "created_at")
    list_filter   = ("notification_type", "is_read")
    search_fields = ("user__phone_number", "title")
    readonly_fields = ("created_at", "read_at")
    ordering      = ("-created_at",)
