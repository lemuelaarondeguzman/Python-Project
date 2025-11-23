#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pythonProject.settings')
django.setup()

from django.contrib.auth.models import User
from myapp.models import Section, Survey, Question, UserProfile, Response, Answer
from django.utils import timezone
from datetime import timedelta

# Create sections
section1, created = Section.objects.get_or_create(
    name="Section A",
    defaults={'description': 'First section', 'created_by': User.objects.first()}
)

section2, created = Section.objects.get_or_create(
    name="Section B", 
    defaults={'description': 'Second section', 'created_by': User.objects.first()}
)

print(f"Created sections: {section1}, {section2}")

# Create a test survey
teacher = User.objects.filter(profile__role='teacher').first()
if not teacher:
    print("No teacher found. Please create a teacher account first.")
    exit()

survey, created = Survey.objects.get_or_create(
    title="Test Survey for Analytics",
    defaults={
        'description': 'A test survey to check analytics',
        'created_by': teacher,
        'due_date': timezone.now() + timedelta(days=7)
    }
)

if created:
    survey.assigned_sections.add(section1, section2)
    print(f"Created survey: {survey}")

# Create test questions
question1, created = Question.objects.get_or_create(
    survey=survey,
    question_text="What is your favorite color?",
    defaults={
        'question_type': 'multiple_choice',
        'choices': ['Red', 'Blue', 'Green', 'Yellow'],
        'is_required': True,
        'order': 1
    }
)

question2, created = Question.objects.get_or_create(
    survey=survey,
    question_text="How satisfied are you with this course?",
    defaults={
        'question_type': 'likert_scale',
        'likert_min': 1,
        'likert_max': 5,
        'likert_labels': ['Very Dissatisfied', 'Dissatisfied', 'Neutral', 'Satisfied', 'Very Satisfied'],
        'is_required': True,
        'order': 2
    }
)

question3, created = Question.objects.get_or_create(
    survey=survey,
    question_text="Any additional comments?",
    defaults={
        'question_type': 'short_answer',
        'is_required': False,
        'order': 3
    }
)

print(f"Created questions: {question1}, {question2}, {question3}")

# Create test responses
students = User.objects.filter(profile__role='student')[:3]
for i, student in enumerate(students):
    response, created = Response.objects.get_or_create(
        survey=survey,
        student=student
    )
    
    if created:
        # Answer for multiple choice
        Answer.objects.create(
            response=response,
            question=question1,
            answer_choice=['Red', 'Blue', 'Green'][i % 3]
        )
        
        # Answer for likert scale
        Answer.objects.create(
            response=response,
            question=question2,
            answer_number=[1, 3, 5][i % 3]
        )
        
        # Answer for short answer
        Answer.objects.create(
            response=response,
            question=question3,
            answer_text=f"Test comment {i+1}"
        )
        
        print(f"Created response for {student.username}")

print("Test data created successfully!")
