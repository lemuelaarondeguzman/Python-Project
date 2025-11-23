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

# Test the expired survey
expired_survey = Survey.objects.get(title="Test Survery")
print(f"Survey: {expired_survey.title}")
print(f"Due Date: {expired_survey.due_date}")
print(f"Current Time: {timezone.now()}")
print(f"Is Open: {expired_survey.is_open}")
print(f"Time Comparison: {timezone.now()} <= {expired_survey.due_date} = {timezone.now() <= expired_survey.due_date}")

# Test with a future date
from datetime import timedelta
future_survey = Survey.objects.filter(is_active=True, due_date__gt=timezone.now()).first()
if future_survey:
    print(f"\nFuture Survey: {future_survey.title}")
    print(f"Due Date: {future_survey.due_date}")
    print(f"Is Open: {future_survey.is_open}")
