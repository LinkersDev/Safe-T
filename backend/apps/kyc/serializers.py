"""DRF serializers for the KYC app."""
from rest_framework import serializers

from apps.users.constants import KycStatus

from .constants import KycDocumentType
from .models import KycDocument, KycProfile


class KycDocumentUploadSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=KycDocumentType.CHOICES)
    file = serializers.FileField()


class KycDocumentSerializer(serializers.ModelSerializer):
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = KycDocument
        fields = [
            "id",
            "document_type",
            "file",
            "status",
            "reviewed_by_name",
            "reviewed_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class KycStatusSerializer(serializers.Serializer):
    """Serializes a user's KYC summary (status + list of documents)."""
    kyc_status = serializers.CharField()
    documents = KycDocumentSerializer(many=True, source="kyc_documents")


class KycProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = KycProfile
        fields = [
            "legal_full_name",
            "date_of_birth",
            "nationality",
            "id_type",
            "id_number",
            "address_line1",
            "address_city",
            "address_country",
            "submitted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["submitted_at", "created_at", "updated_at"]


class KycProfileSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = KycProfile
        fields = [
            "legal_full_name",
            "date_of_birth",
            "nationality",
            "id_type",
            "id_number",
            "address_line1",
            "address_city",
            "address_country",
        ]


class StaffApproveKycSerializer(serializers.Serializer):
    """Empty body — approval has no required payload."""
    pass


class StaffRejectKycSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=5, max_length=500)


class StaffRejectDocumentSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=5, max_length=500)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class StaffApproveDocumentSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class KycUserSummarySerializer(serializers.Serializer):
    """Minimal user info returned in the KYC review queue."""
    id = serializers.IntegerField()
    phone_number = serializers.CharField()
    full_name = serializers.CharField()
    kyc_status = serializers.CharField()
    pending_document_count = serializers.SerializerMethodField()

    def get_pending_document_count(self, obj) -> int:
        return obj.kyc_documents.filter(status="PENDING").count()
