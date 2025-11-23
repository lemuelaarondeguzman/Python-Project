from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('myapp', '0006_survey_is_published'),
    ]

    operations = [
        migrations.AddField(
            model_name='survey',
            name='time_limit_minutes',
            field=models.PositiveIntegerField(blank=True, help_text='Optional time limit (in minutes) for completing the survey.', null=True),
        ),
        migrations.CreateModel(
            name='StudentSurveyProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answers', models.JSONField(blank=True, default=dict)),
                ('time_spent_seconds', models.PositiveIntegerField(default=0)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_submitted', models.BooleanField(default=False)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='survey_progress', to='auth.user')),
                ('survey', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress_records', to='myapp.survey')),
            ],
            options={
                'ordering': ['-updated_at'],
                'unique_together': {('survey', 'student')},
            },
        ),
    ]





