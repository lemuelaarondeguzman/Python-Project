#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pythonProject.settings')
django.setup()

from django.utils import timezone
from myapp.models import Survey

# Check all surveys and their status
surveys = Survey.objects.filter(is_active=True)
print("Current time:", timezone.now())
print("\nSurvey Status Check:")
print("-" * 50)

for survey in surveys:
    print(f"Survey: {survey.title}")
    print(f"  Due Date: {survey.due_date}")
    print(f"  Is Active: {survey.is_active}")
    print(f"  Is Open: {survey.is_open}")
    print(f"  Time Check: {timezone.now()} <= {survey.due_date} = {timezone.now() <= survey.due_date}")
    print("-" * 50)
