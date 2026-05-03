"""
Data migration: ensure ADMIN role has required permissions.

This is intentionally additive (no deletions) to fix dev DBs where the
admin permission links were not created correctly.
"""

from django.db import migrations


def ensure_admin_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")
    RolePermission = apps.get_model("users", "RolePermission")

    try:
        admin = Role.objects.get(code="ADMIN")
    except Role.DoesNotExist:
        return

    from apps.users.constants import ADMIN_DEFAULT_PERMISSION_CODES

    perms = Permission.objects.filter(code__in=ADMIN_DEFAULT_PERMISSION_CODES)
    for perm in perms:
        RolePermission.objects.get_or_create(role=admin, permission=perm)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_manage_system_and_admin_role_permissions"),
    ]

    operations = [
        migrations.RunPython(ensure_admin_permissions, noop_reverse),
    ]

