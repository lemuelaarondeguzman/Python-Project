from django.db import migrations
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from datetime import timedelta


def seed_demo_content(apps, schema_editor):
    Section = apps.get_model('myapp', 'Section')
    Survey = apps.get_model('myapp', 'Survey')
    Question = apps.get_model('myapp', 'Question')
    Response = apps.get_model('myapp', 'Response')
    Answer = apps.get_model('myapp', 'Answer')
    UserProfile = apps.get_model('myapp', 'UserProfile')
    User = apps.get_model('auth', 'User')

    sections = list(Section.objects.all())
    if not sections:
        return

    teacher_profile = UserProfile.objects.filter(role='teacher').select_related('user').first()
    if teacher_profile:
        teacher = teacher_profile.user
    else:
        teacher = User.objects.create(
            username='demo_teacher',
            first_name='Demo',
            last_name='Instructor',
            email='demo_teacher@example.com',
            password=make_password('Password123')
        )
        UserProfile.objects.create(
            user=teacher,
            role='teacher',
            section=None,
            is_verified=True
        )

    # Create demo students
    students = []
    for idx in range(1, 5):
        username = f'demo_student_{idx}'
        student, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': f'Demo {idx}',
                'last_name': 'Student',
                'email': f'demo_student_{idx}@example.com',
                'password': make_password('Password123')
            }
        )
        UserProfile.objects.update_or_create(
            user=student,
            defaults={
                'role': 'student',
                'section': sections[(idx - 1) % len(sections)],
                'is_verified': True
            }
        )
        students.append(student)

    # Create sample surveys if none exist for teacher
    sample_titles = [
        'Weekly Reflection',
        'Project Preparation Check'
    ]

    for offset, title in enumerate(sample_titles, start=1):
        survey, created = Survey.objects.get_or_create(
            title=title,
            created_by=teacher,
            defaults={
                'description': f'Sample survey "{title}" for demonstration.',
                'due_date': timezone.now() + timedelta(days=7 + offset),
                'is_published': True,
                'is_active': True,
                'is_archived': False
            }
        )
        if created:
            survey.assigned_sections.set([sections[(offset - 1) % len(sections)]])

            Question.objects.create(
                survey=survey,
                question_text='How confident do you feel about this week’s lessons?',
                question_type='likert_scale',
                is_required=True,
                order=0,
                likert_min=1,
                likert_max=5,
                likert_labels=["Low", "Below Avg", "Neutral", "Good", "Great"]
            )
            Question.objects.create(
                survey=survey,
                question_text='What topics do you want to revisit?',
                question_type='short_answer',
                is_required=False,
                order=1
            )

        questions = list(survey.questions.all())
        if not questions:
            continue

        eligible_students = [
            s for s in students if s.profile.section_id in survey.assigned_sections.values_list('id', flat=True)
        ]
        for student in eligible_students[:2]:
            response, created = Response.objects.get_or_create(
                survey=survey,
                student=student,
                defaults={'submitted_at': timezone.now()}
            )
            if created:
                for question in questions:
                    if question.question_type == 'likert_scale':
                        Answer.objects.create(
                            response=response,
                            question=question,
                            answer_number=4
                        )
                    else:
                        Answer.objects.create(
                            response=response,
                            question=question,
                            answer_text='Need more examples on the latest topic.'
                        )


def remove_demo_content(apps, schema_editor):
    # No-op reversal – demo data can be removed manually if needed.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0008_survey_is_archived_userprofile_is_verified_default'),
    ]

    operations = [
        migrations.RunPython(seed_demo_content, remove_demo_content),
    ]


