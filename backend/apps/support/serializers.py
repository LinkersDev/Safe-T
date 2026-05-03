"""DRF serializers for the support app."""
from rest_framework import serializers

from .constants import TicketCategory
from .models import Notification, SupportTicket, SupportTicketMessage


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = [
            "id", "notification_type", "title", "message",
            "is_read", "read_at", "reference_type", "reference_id", "created_at",
        ]
        read_only_fields = fields


class SupportTicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True, default=None)

    class Meta:
        model  = SupportTicketMessage
        fields = ["id", "sender_name", "body", "is_internal", "created_at"]
        read_only_fields = fields


class SupportTicketSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(
        source="assigned_to.full_name", read_only=True, default=None
    )
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True, default=None)
    user_phone_number = serializers.CharField(source="user.phone_number", read_only=True, default=None)

    class Meta:
        model  = SupportTicket
        fields = [
            "id", "subject", "category", "status",
            "user_id", "user_full_name", "user_phone_number",
            "assigned_to_name", "resolved_at", "closed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class SupportTicketDetailSerializer(SupportTicketSerializer):
    messages = SupportTicketMessageSerializer(many=True, read_only=True)

    class Meta(SupportTicketSerializer.Meta):
        fields = SupportTicketSerializer.Meta.fields + ["messages"]


class CreateTicketSerializer(serializers.Serializer):
    subject  = serializers.CharField(min_length=5, max_length=200)
    body     = serializers.CharField(min_length=10)
    category = serializers.ChoiceField(choices=TicketCategory.CHOICES, default=TicketCategory.GENERAL)


class ReplyTicketSerializer(serializers.Serializer):
    body = serializers.CharField(min_length=1)


class StaffReplyTicketSerializer(serializers.Serializer):
    body        = serializers.CharField(min_length=1)
    is_internal = serializers.BooleanField(default=False)


class StaffAssignTicketSerializer(serializers.Serializer):
    """No payload needed — staff assigns to themselves."""
    pass


class StaffResolveTicketSerializer(serializers.Serializer):
    """No payload needed."""
    pass
