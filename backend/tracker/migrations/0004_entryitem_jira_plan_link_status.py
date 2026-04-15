from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0003_slack_thread_and_reply_ts"),
    ]

    operations = [
        migrations.AddField(
            model_name="entryitem",
            name="jira_issue_key",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="entryitem",
            name="jira_issue_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="entryitem",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("in_progress", "In Progress"),
                    ("blocked", "Blocked"),
                    ("closed", "Closed"),
                ],
                default="open",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="entryitem",
            name="plan_item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="update_lines",
                to="tracker.entryitem",
            ),
        ),
    ]
