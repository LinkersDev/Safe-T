"""
Data migration: ensure TELLER role has required permissions.

Why:
  - Frontend gates staff modules by permissions.
  - Staff account lookup and teller operations must work out-of-the-box in dev DBs.
"""

from django.db import migrations


def ensure_teller_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")
    RolePermission = apps.get_model("users", "RolePermission")

    try:
        teller = Role.objects.get(code="TELLER")
    except Role.DoesNotExist:
        return

    required_codes = [
        # Account management (lookup + restrictions)
        "view_all_accounts",
        "freeze_account",
        "unfreeze_account",
        # Teller operations
        "staff_register_customer",
        "staff_deposit",
        "staff_withdraw",
        "staff_view_account_transactions",
    ]

    perms = Permission.objects.filter(code__in=required_codes)
    for perm in perms:
        RolePermission.objects.get_or_create(role=teller, permission=perm)

    # Explicitly remove user-list access if it was granted historically.
    RolePermission.objects.filter(role=teller, permission__code="view_all_users").delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_ensure_admin_permissions"),
    ]

    operations = [
        migrations.RunPython(ensure_teller_permissions, noop_reverse),
    ]

