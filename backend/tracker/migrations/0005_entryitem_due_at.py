from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0004_entryitem_jira_plan_link_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="entryitem",
            name="due_at",
            field=models.DateField(blank=True, null=True),
        ),
    ]

