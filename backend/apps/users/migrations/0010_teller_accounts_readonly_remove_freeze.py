"""
Remove freeze/unfreeze from TELLER role — Account Management read-only for tellers.

Restriction actions remain available to roles that retain these permissions (e.g. ADMIN).
"""

from django.db import migrations


def remove_teller_freeze_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")
    RolePermission = apps.get_model("users", "RolePermission")

    try:
        teller = Role.objects.get(code="TELLER")
    except Role.DoesNotExist:
        return

    perm_ids = list(
        Permission.objects.filter(code__in=("freeze_account", "unfreeze_account")).values_list("pk", flat=True)
    )
    if not perm_ids:
        return
    RolePermission.objects.filter(role=teller, permission_id__in=perm_ids).delete()


def noop_reverse(apps, schema_editor):
    """Re-attach teller freeze perms only if both rows exist (best-effort rollback)."""
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")
    RolePermission = apps.get_model("users", "RolePermission")

    try:
        teller = Role.objects.get(code="TELLER")
    except Role.DoesNotExist:
        return

    for code in ("freeze_account", "unfreeze_account"):
        try:
            perm = Permission.objects.get(code=code)
            RolePermission.objects.get_or_create(role=teller, permission=perm)
        except Permission.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_staff_profile"),
    ]

    operations = [
        migrations.RunPython(remove_teller_freeze_permissions, noop_reverse),
    ]
