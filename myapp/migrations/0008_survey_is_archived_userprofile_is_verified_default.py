from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0007_survey_time_limit_and_progress'),
    ]

    operations = [
        migrations.AddField(
            model_name='survey',
            name='is_archived',
            field=models.BooleanField(default=False, help_text='Archived surveys are hidden from students until restored.'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='is_verified',
            field=models.BooleanField(default=True, help_text='Whether the student account has been verified by a teacher'),
        ),
    ]


