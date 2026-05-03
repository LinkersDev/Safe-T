from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0007_seed_teller_operation_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="first_login_completed",
            field=models.BooleanField(default=True),
        ),
    ]

