"""
Grant ADMIN role teller cash-ops permissions (deposit/withdraw).

This enables admin access to staff deposit/withdraw pages.
"""

from django.db import migrations


def grant_admin_cash_ops(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")
    RolePermission = apps.get_model("users", "RolePermission")

    try:
        admin = Role.objects.get(code="ADMIN")
    except Role.DoesNotExist:
        return

    perms = Permission.objects.filter(code__in=("staff_deposit", "staff_withdraw"))
    for perm in perms:
        RolePermission.objects.get_or_create(role=admin, permission=perm)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0010_teller_accounts_readonly_remove_freeze"),
    ]

    operations = [
        migrations.RunPython(grant_admin_cash_ops, noop_reverse),
    ]

