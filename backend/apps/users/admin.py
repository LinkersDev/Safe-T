from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Role, Permission, RolePermission, User, PhoneNumber


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_staff_role", "is_system_role", "created_at")
    search_fields = ("code", "name")
    list_filter = ("is_staff_role", "is_system_role")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "module")
    search_fields = ("code", "name", "module")
    list_filter = ("module",)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission", "granted_by", "created_at")
    list_filter = ("role",)
    autocomplete_fields = ("role", "permission")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("phone_number", "full_name", "role", "status", "kyc_status", "created_at")
    list_filter = ("status", "kyc_status", "role")
    search_fields = ("phone_number", "full_name")
    readonly_fields = ("created_at", "updated_at", "last_login_at", "approved_at")
    ordering      = ("-created_at",)
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {"fields": ("phone_number", "phone_number_normalized", "password", "pin_hash")}),
        ("Personal info", {"fields": ("full_name",)}),
        ("Status", {"fields": ("status", "kyc_status", "is_phone_verified", "role")}),
        ("Activation", {"fields": ("approved_by", "approved_at", "rejection_reason", "blocked_reason")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_login_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone_number", "full_name", "password1", "password2"),
        }),
    )


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "label", "is_verified", "is_active")
    list_filter = ("label", "is_verified", "is_active")
    search_fields = ("phone_number",)
