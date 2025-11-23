from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.hashers import make_password
from datetime import timedelta
import random

from myapp.models import (
    Section,
    Survey,
    Question,
    Response,
    Answer,
    UserProfile,
)


class Command(BaseCommand):
    help = "Seed demo students and surveys using the existing sections."

    def handle(self, *args, **options):
        sections = list(Section.objects.all())
        if not sections:
            self.stdout.write(self.style.WARNING("No sections found. Create sections first."))
            return

        teacher = User.objects.filter(profile__role='teacher').first()
        if not teacher:
            teacher = User.objects.create(
                username='demo_teacher',
                first_name='Demo',
                last_name='Instructor',
                email='demo_teacher@example.com',
                password=make_password('Password123')
            )
            UserProfile.objects.create(user=teacher, role='teacher', section=None, is_verified=True)
            self.stdout.write(self.style.SUCCESS("Created demo teacher account (username: demo_teacher / Password123)."))

        self._seed_students(sections)
        self._seed_surveys(sections, teacher)

        self.stdout.write(self.style.SUCCESS("Demo data seeding complete."))

    @transaction.atomic
    def _seed_students(self, sections):
        demo_students = []
        for idx in range(1, 7):
            username = f"demo_student_{idx}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': f"Demo {idx}",
                    'last_name': "Student",
                    'email': f"demo_student_{idx}@example.com",
                    'password': make_password('Password123')
                }
            )
            if created or not hasattr(user, 'profile'):
                section = random.choice(sections)
                UserProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        'role': 'student',
                        'section': section,
                        'is_verified': True
                    }
                )
                self.stdout.write(self.style.SUCCESS(f"Ensured student account {username} (section: {section.name})."))
            demo_students.append(user)
        self.demo_students = demo_students

    @transaction.atomic
    def _seed_surveys(self, sections, teacher):
        sample_titles = [
            "Class Feedback",
            "Weekly Check-in",
            "Project Readiness Survey",
        ]

        for idx, title in enumerate(sample_titles, start=1):
            due_date = timezone.now() + timedelta(days=7 + idx)
            survey, created = Survey.objects.get_or_create(
                title=title,
                created_by=teacher,
                defaults={
                    'description': f"Automated sample survey #{idx}",
                    'due_date': due_date,
                    'is_published': True,
                    'is_active': True,
                }
            )
            if created:
                section = sections[(idx - 1) % len(sections)]
                survey.assigned_sections.set([section])
                self._create_sample_questions(survey)
                self.stdout.write(self.style.SUCCESS(f"Created survey '{title}' for {section.name}."))
            self._seed_responses(survey)

    def _create_sample_questions(self, survey):
        Question.objects.create(
            survey=survey,
            question_text="How confident do you feel about this week's lessons?",
            question_type='likert_scale',
            is_required=True,
            order=0,
            likert_min=1,
            likert_max=5,
            likert_labels=["Not Confident", "Slightly", "Neutral", "Confident", "Very Confident"]
        )
        Question.objects.create(
            survey=survey,
            question_text="What topics would you like to revisit?",
            question_type='short_answer',
            is_required=False,
            order=1,
        )

    def _seed_responses(self, survey):
        if not hasattr(self, 'demo_students'):
            return
        questions = list(survey.questions.all())
        if not questions:
            return

        assigned_sections = set(survey.assigned_sections.values_list('id', flat=True))
        eligible_students = [
            student for student in self.demo_students
            if student.profile.section_id in assigned_sections
        ]
        for student in eligible_students[:3]:
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
                            answer_number=random.randint(question.likert_min, question.likert_max)
                        )
                    elif question.question_type == 'short_answer':
                        Answer.objects.create(
                            response=response,
                            question=question,
                            answer_text="I'd like to review the latest lab."
                        )


