from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ussd", "0002_alter_ussdsession_current_step"),
    ]

    operations = [
        migrations.AddField(
            model_name="ussdsession",
            name="flow_type",
            field=models.CharField(
                choices=[
                    ("USSD_INIT", "USSD_INIT"),
                    ("FARM_REG_U", "FARM_REG_U"),
                    ("FARM_REG", "FARM_REG"),
                ],
                default="USSD_INIT",
                max_length=100,
            ),
        ),
    ]