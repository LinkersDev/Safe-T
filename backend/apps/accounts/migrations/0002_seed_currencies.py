"""
Data migration: seed initial currencies (USD, EUR).
USD is the default currency used when creating accounts on user approval.
"""
from django.db import migrations

from apps.accounts.constants import SEED_CURRENCIES


def seed_currencies(apps, schema_editor):
    Currency = apps.get_model("accounts", "Currency")
    for code, name, symbol, decimal_places in SEED_CURRENCIES:
        Currency.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "symbol": symbol,
                "decimal_places": decimal_places,
                "is_active": True,
            },
        )


def unseed_currencies(apps, schema_editor):
    Currency = apps.get_model("accounts", "Currency")
    codes = [row[0] for row in SEED_CURRENCIES]
    Currency.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_currencies, reverse_code=unseed_currencies),
    ]
