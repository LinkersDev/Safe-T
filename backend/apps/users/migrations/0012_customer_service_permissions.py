"""
Ensure CUSTOMER_SERVICE role has required permissions.

Why:
  - Frontend assumes CUSTOMER_SERVICE can manage support tickets.
  - Some deployments seed roles/permissions but do not link role-permissions
    for CUSTOMER_SERVICE, which causes 403s and "Degraded mode" in the staff UI.
"""

from django.db import migrations


def ensure_cs_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")
    RolePermission = apps.get_model("users", "RolePermission")

    try:
        cs = Role.objects.get(code="CUSTOMER_SERVICE")
    except Role.DoesNotExist:
        return

    needed_perm_codes = [
        "manage_support_tickets",
        "unlock_user",
        "reset_user_credentials",
    ]

    perms = Permission.objects.filter(code__in=needed_perm_codes)
    for perm in perms:
        RolePermission.objects.get_or_create(role=cs, permission=perm)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0011_admin_teller_cash_ops_permissions"),
    ]

    operations = [
        migrations.RunPython(ensure_cs_permissions, noop_reverse),
    ]

