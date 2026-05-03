"""
Data migration: seeds system roles and permissions.
Must run after 0001_initial.
"""
from django.db import migrations

from apps.users.constants import SEED_PERMISSIONS, SEED_ROLES


def seed_roles(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    for code, name, description, is_staff_role, is_system_role in SEED_ROLES:
        Role.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "description": description,
                "is_staff_role": is_staff_role,
                "is_system_role": is_system_role,
            },
        )


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    for code, name, module, description in SEED_PERMISSIONS:
        Permission.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "module": module,
                "description": description,
            },
        )


def reverse_seeds(apps, schema_editor):
    # Only remove non-system records during reversal; system roles are protected
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, reverse_code=reverse_seeds),
        migrations.RunPython(seed_permissions, reverse_code=reverse_seeds),
    ]
