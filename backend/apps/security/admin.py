from django.contrib import admin
from .models import OTPRequest, LoginLog, UserDevice, AccountLockEvent, PasswordResetAudit


@admin.register(OTPRequest)
class OTPRequestAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "request_type", "status", "attempts_count", "expires_at", "created_at")
    list_filter = ("request_type", "status", "sent_via")
    search_fields = ("phone_number",)
    readonly_fields = ("otp_hash", "created_at", "verified_at")


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display  = ("phone_number", "status", "risk_score", "ip_address", "device", "location_country", "attempted_at")
    list_filter   = ("status", "location_country")
    search_fields = ("phone_number", "ip_address", "device_id")
    readonly_fields = ("attempted_at", "risk_score")
    date_hierarchy = "attempted_at"


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "device_name", "platform", "is_trusted", "is_active", "last_seen_at")
    list_filter = ("platform", "is_trusted", "is_active")
    search_fields = ("device_uuid", "device_name")


@admin.register(AccountLockEvent)
class AccountLockEventAdmin(admin.ModelAdmin):
    list_display = ("user", "event_type", "trigger_source", "is_active", "occurred_at")
    list_filter = ("event_type", "is_active")
    search_fields = ("user__phone_number",)
    readonly_fields = ("occurred_at",)


@admin.register(PasswordResetAudit)
class PasswordResetAuditAdmin(admin.ModelAdmin):
    list_display = ("user", "reset_type", "initiated_by", "success", "created_at")
    list_filter = ("reset_type", "success")
    search_fields = ("user__phone_number",)
    readonly_fields = ("created_at",)
