"""
Migration: change QRPayment.currency default from 'SAR' to 'USD'.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
        ("accounts", "0002_seed_currencies"),
    ]

    operations = [
        migrations.AlterField(
            model_name="qrpayment",
            name="currency",
            field=models.ForeignKey(
                default="USD",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="qr_payments",
                to="accounts.currency",
            ),
        ),
    ]
