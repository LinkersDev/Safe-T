"""
Migration: extend KycStatus choices (add NOT_SUBMITTED, APPROVED; drop VERIFIED)
and change the default from PENDING to NOT_SUBMITTED.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_seed_roles_permissions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="kyc_status",
            field=models.CharField(
                choices=[
                    ("NOT_SUBMITTED", "Not Submitted"),
                    ("PENDING", "Pending Review"),
                    ("APPROVED", "Approved"),
                    ("REJECTED", "Rejected"),
                ],
                default="NOT_SUBMITTED",
                max_length=30,
            ),
        ),
    ]
