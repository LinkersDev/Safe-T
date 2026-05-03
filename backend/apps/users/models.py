"""
Users app models:
  Role, Permission, RolePermission, User, PhoneNumber
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from .constants import UserStatus, KycStatus, PhoneLabel


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------

class Role(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_staff_role = models.BooleanField(default=False)
    is_system_role = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "roles"
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_staff_role"]),
        ]

    def __str__(self) -> str:
        return self.name

    def delete(self, *args, **kwargs):
        if self.is_system_role:
            raise ValueError(f"System role '{self.code}' cannot be deleted.")
        super().delete(*args, **kwargs)


# ---------------------------------------------------------------------------
# Permission
# ---------------------------------------------------------------------------

class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    module = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "permissions"
        indexes = [
            models.Index(fields=["module", "code"]),
        ]

    def __str__(self) -> str:
        return self.code


# ---------------------------------------------------------------------------
# RolePermission
# ---------------------------------------------------------------------------

class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="role_permissions",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.PROTECT,
        related_name="permission_roles",
    )
    granted_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="granted_role_permissions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "role_permissions"
        unique_together = [("role", "permission")]
        indexes = [
            models.Index(fields=["role", "permission"]),
        ]

    def __str__(self) -> str:
        return f"{self.role.code} → {self.permission.code}"


# ---------------------------------------------------------------------------
# UserManager
# ---------------------------------------------------------------------------

class UserManager(BaseUserManager):
    """Custom manager — phone_number is the unique identifier, not username/email."""

    def _create_user(self, phone_number: str, password: str, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required.")
        phone_number = self._normalize_phone(phone_number)
        user = self.model(
            phone_number=phone_number,
            phone_number_normalized=phone_number,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone_number: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone_number, password, **extra_fields)

    def create_superuser(self, phone_number: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", UserStatus.ACTIVE)
        return self._create_user(phone_number, password, **extra_fields)

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Strip spaces and dashes; enforce E.164 in service layer."""
        return phone.strip().replace(" ", "").replace("-", "")


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(AbstractBaseUser, PermissionsMixin):
    """
    Master identity model for all system actors.
    Login identifier: phone_number only.
    No email field. No username field.
    """
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, unique=True)
    phone_number_normalized = models.CharField(max_length=20, unique=True)

    # Hashed PIN separate from password
    pin_hash = models.CharField(max_length=255, blank=True)

    # Account lifecycle
    status = models.CharField(
        max_length=30,
        choices=UserStatus.CHOICES,
        default=UserStatus.PENDING_VERIFICATION,
    )
    kyc_status = models.CharField(
        max_length=30,
        choices=KycStatus.CHOICES,
        default=KycStatus.NOT_SUBMITTED,
    )
    is_phone_verified = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)

    # First login onboarding (OTP-first setup)
    first_login_completed = models.BooleanField(default=True)

    # Staff activation fields
    approved_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_users",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    blocked_reason = models.TextField(blank=True)

    # Django admin compatibility
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["phone_number_normalized"]),
            models.Index(fields=["role", "status"]),
            models.Index(fields=["kyc_status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone_number})"

    @property
    def is_pending(self) -> bool:
        return self.status == UserStatus.PENDING_VERIFICATION

    @property
    def is_active_customer(self) -> bool:
        return self.status == UserStatus.ACTIVE


# ---------------------------------------------------------------------------
# StaffProfile
# ---------------------------------------------------------------------------

class StaffProfile(models.Model):
    """
    Staff-only profile fields (HR/branch metadata).
    Kept separate from User to avoid bloating the core identity model.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="staff_profile",
    )

    employee_id = models.CharField(max_length=64, blank=True)
    department = models.CharField(max_length=100, blank=True)
    branch = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)

    address_line1 = models.CharField(max_length=255, blank=True)
    address_city = models.CharField(max_length=120, blank=True)
    address_country = models.CharField(max_length=120, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_profiles"
        indexes = [
            models.Index(fields=["employee_id"]),
            models.Index(fields=["department"]),
            models.Index(fields=["branch"]),
        ]

    def __str__(self) -> str:
        return f"StaffProfile(user={self.user_id})"


# ---------------------------------------------------------------------------
# PhoneNumber  (secondary / WhatsApp numbers)
# ---------------------------------------------------------------------------

class PhoneNumber(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="phone_numbers",
    )
    phone_number = models.CharField(max_length=20, unique=True)
    phone_number_normalized = models.CharField(max_length=20, unique=True)
    label = models.CharField(
        max_length=30,
        choices=PhoneLabel.CHOICES,
        default=PhoneLabel.SECONDARY,
    )
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phone_numbers"
        indexes = [
            models.Index(fields=["phone_number_normalized"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} — {self.phone_number} ({self.label})"
