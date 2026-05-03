"""Users app serializers — Phase 1 stubs, expanded in Phase 2."""
from rest_framework import serializers

from .models import User, Role, StaffProfile


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "code", "name", "is_staff_role")


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "phone_number",
            "status",
            "kyc_status",
            "is_phone_verified",
            "is_active",
            "role",
            "created_at",
        )
        read_only_fields = fields


class StaffProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffProfile
        fields = (
            "employee_id",
            "department",
            "branch",
            "job_title",
            "address_line1",
            "address_city",
            "address_country",
        )


class StaffRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=30)
    role_code = serializers.CharField(max_length=50)

    employee_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    branch = serializers.CharField(max_length=100, required=False, allow_blank=True)
    job_title = serializers.CharField(max_length=100, required=False, allow_blank=True)

    address_line1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    address_country = serializers.CharField(max_length=120, required=False, allow_blank=True)
