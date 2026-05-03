"""Seed manage_system permission and enforce explicit ADMIN permission set."""

from django.db import migrations


def seed_manage_system_and_link_admin(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")
    RolePermission = apps.get_model("users", "RolePermission")

    Permission.objects.get_or_create(
        code="manage_system",
        defaults={
            "name": "Manage System",
            "module": "ledger",
            "description": "Can archive transactions and system-level ledger ops",
        },
    )

    try:
        admin = Role.objects.get(code="ADMIN")
    except Role.DoesNotExist:
        return

    from apps.users.constants import ADMIN_DEFAULT_PERMISSION_CODES

    required_perms = Permission.objects.filter(code__in=ADMIN_DEFAULT_PERMISSION_CODES)

    for perm in required_perms:
        RolePermission.objects.get_or_create(role=admin, permission=perm)

    # Enforce a controlled ADMIN permission set (no accidental extra grants).
    RolePermission.objects.filter(role=admin).exclude(
        permission__code__in=ADMIN_DEFAULT_PERMISSION_CODES
    ).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_user_kyc_status_update"),
    ]

    operations = [
        migrations.RunPython(seed_manage_system_and_link_admin, noop_reverse),
    ]
