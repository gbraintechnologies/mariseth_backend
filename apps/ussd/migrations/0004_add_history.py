from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ussd", "0003_add_flow_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="ussdsession",
            name="history",
            field=models.JSONField(default=list),
        )
    ]