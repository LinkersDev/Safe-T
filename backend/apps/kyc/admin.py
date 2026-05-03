from django.contrib import admin

from .models import KycDocument


@admin.register(KycDocument)
class KycDocumentAdmin(admin.ModelAdmin):
    list_display  = ("id", "user", "document_type", "status", "reviewed_by", "reviewed_at", "created_at")
    list_filter   = ("status", "document_type")
    search_fields = ("user__phone_number", "user__full_name")
    readonly_fields = ("created_at", "updated_at", "reviewed_at")
    ordering      = ("-created_at",)
