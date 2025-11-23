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

# Check survey ID 8
try:
    survey = Survey.objects.get(id=8)
    print(f"Survey ID 8: {survey.title}")
    print(f"Due Date: {survey.due_date}")
    print(f"Current Time: {timezone.now()}")
    print(f"Is Open: {survey.is_open}")
    print(f"Time Comparison: {timezone.now()} <= {survey.due_date} = {timezone.now() <= survey.due_date}")
except Survey.DoesNotExist:
    print("Survey ID 8 does not exist")

# Check all surveys
print("\nAll Surveys:")
for survey in Survey.objects.all():
    print(f"ID {survey.id}: {survey.title} - Due: {survey.due_date} - Open: {survey.is_open}")
