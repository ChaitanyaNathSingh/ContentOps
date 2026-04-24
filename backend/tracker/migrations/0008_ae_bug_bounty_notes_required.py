from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0007_ae_daily_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='aedailyupdate',
            name='bug_bounty_reviewed',
            field=models.PositiveIntegerField(default=0, verbose_name='Bug Bounty Reviewed'),
        ),
        migrations.AlterField(
            model_name='aedailyupdate',
            name='notes',
            field=models.TextField(blank=False, default=''),
            preserve_default=False,
        ),
    ]
