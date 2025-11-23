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

# Update existing sections
try:
    section_a = Section.objects.get(name="Section A")
    section_a.name = "BSIT 4E G1"
    section_a.description = "BSIT 4E Group 1"
    section_a.save()
    print(f"Updated section: {section_a}")
except Section.DoesNotExist:
    teacher = User.objects.filter(profile__role='teacher').first()
    if teacher:
        section_a = Section.objects.create(
            name="BSIT 4E G1",
            description="BSIT 4E Group 1",
            created_by=teacher
        )
        print(f"Created section: {section_a}")

try:
    section_b = Section.objects.get(name="Section B")
    section_b.name = "BSIT 4E G2"
    section_b.description = "BSIT 4E Group 2"
    section_b.save()
    print(f"Updated section: {section_b}")
except Section.DoesNotExist:
    teacher = User.objects.filter(profile__role='teacher').first()
    if teacher:
        section_b = Section.objects.create(
            name="BSIT 4E G2",
            description="BSIT 4E Group 2",
            created_by=teacher
        )
        print(f"Created section: {section_b}")

# Assign students to specific sections
students = User.objects.filter(profile__role='student')
for i, student in enumerate(students):
    if i % 2 == 0:
        student.profile.section = section_a
    else:
        student.profile.section = section_b
    student.profile.save()
    print(f"Assigned {student.username} to {student.profile.section}")

# Create test surveys for specific sections
teacher = User.objects.filter(profile__role='teacher').first()
if teacher:
    # Survey for BSIT 4E G1 only
    survey_g1, created = Survey.objects.get_or_create(
        title="Survey for BSIT 4E G1 Only",
        defaults={
            'description': 'This survey is only for BSIT 4E G1 students',
            'created_by': teacher,
            'due_date': timezone.now() + timedelta(days=7)
        }
    )
    if created:
        survey_g1.assigned_sections.add(section_a)
        print(f"Created survey for G1: {survey_g1}")
    
    # Survey for BSIT 4E G2 only
    survey_g2, created = Survey.objects.get_or_create(
        title="Survey for BSIT 4E G2 Only",
        defaults={
            'description': 'This survey is only for BSIT 4E G2 students',
            'created_by': teacher,
            'due_date': timezone.now() + timedelta(days=7)
        }
    )
    if created:
        survey_g2.assigned_sections.add(section_b)
        print(f"Created survey for G2: {survey_g2}")
    
    # Survey for both sections
    survey_both, created = Survey.objects.get_or_create(
        title="Survey for Both Groups",
        defaults={
            'description': 'This survey is for both BSIT 4E G1 and G2 students',
            'created_by': teacher,
            'due_date': timezone.now() + timedelta(days=7)
        }
    )
    if created:
        survey_both.assigned_sections.add(section_a, section_b)
        print(f"Created survey for both groups: {survey_both}")

print("Section updates completed successfully!")
