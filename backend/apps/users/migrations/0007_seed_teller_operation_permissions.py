"""
Data migration: seed teller operation permissions and link to TELLER role.

Why:
  - These permission codes were added after initial seed migrations.
  - Existing databases need the Permission rows created + linked.
"""

from django.db import migrations


def seed_teller_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")
    RolePermission = apps.get_model("users", "RolePermission")

    perms = [
        ("staff_register_customer", "Register Customer", "teller", "Can register new customer accounts"),
        ("staff_deposit", "Deposit", "teller", "Can deposit money into customer accounts"),
        ("staff_withdraw", "Withdraw", "teller", "Can withdraw money from customer accounts"),
        ("staff_view_account_transactions", "View Account Transactions", "teller", "Can view transactions for a customer account"),
    ]

    created = []
    for code, name, module, description in perms:
        perm, was_created = Permission.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "module": module,
                "description": description,
            },
        )
        if was_created:
            created.append(code)

    try:
        teller = Role.objects.get(code="TELLER")
    except Role.DoesNotExist:
        return

    for code, *_rest in perms:
        perm = Permission.objects.filter(code=code).first()
        if perm is not None:
            RolePermission.objects.get_or_create(role=teller, permission=perm)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_ensure_teller_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_teller_permissions, noop_reverse),
    ]

