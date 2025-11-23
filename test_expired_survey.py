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
from datetime import timedelta
from myapp.models import Survey

# Find a survey and set its due date to the past
survey = Survey.objects.filter(is_active=True).first()
if survey:
    # Set due date to 1 day ago
    survey.due_date = timezone.now() - timedelta(days=1)
    survey.save()
    print(f"Updated survey '{survey.title}' due date to: {survey.due_date}")
    print(f"Survey is now {'OPEN' if survey.is_open else 'CLOSED'}")
else:
    print("No active surveys found")
