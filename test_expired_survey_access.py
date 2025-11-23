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

# Test the expired survey (ID 1)
expired_survey = Survey.objects.get(id=1)
print(f"Expired Survey: {expired_survey.title}")
print(f"Due Date: {expired_survey.due_date}")
print(f"Current Time: {timezone.now()}")
print(f"Is Open: {expired_survey.is_open}")
print(f"Should be accessible: {expired_survey.is_open}")

# Test a future survey (ID 8)
future_survey = Survey.objects.get(id=8)
print(f"\nFuture Survey: {future_survey.title}")
print(f"Due Date: {future_survey.due_date}")
print(f"Current Time: {timezone.now()}")
print(f"Is Open: {future_survey.is_open}")
print(f"Should be accessible: {future_survey.is_open}")

# Let's also set survey ID 8 to be expired
from datetime import timedelta
future_survey.due_date = timezone.now() - timedelta(hours=1)
future_survey.save()
print(f"\nAfter setting survey 8 to expired:")
print(f"Is Open: {future_survey.is_open}")
print(f"Should be accessible: {future_survey.is_open}")
