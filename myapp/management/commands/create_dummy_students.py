from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth.hashers import make_password
import random

from myapp.models import Section, UserProfile


class Command(BaseCommand):
    help = "Create 15 dummy student accounts for testing."

    def handle(self, *args, **options):
        sections = list(Section.objects.all())
        if not sections:
            self.stdout.write(self.style.WARNING("No sections found. Create sections first."))
            return

        first_names = [
            "John", "Jane", "Michael", "Sarah", "David", "Emily", "James", "Jessica",
            "Robert", "Amanda", "William", "Melissa", "Richard", "Michelle", "Joseph"
        ]
        last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas"
        ]

        created_count = 0
        with transaction.atomic():
            for idx in range(1, 16):
                first_name = first_names[idx - 1]
                last_name = last_names[idx - 1]
                username = f"student_{idx:02d}"
                email = f"student_{idx:02d}@example.com"
                
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
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
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Created/Updated student account: {username} ({first_name} {last_name}) - Section: {section.name}"
                    ))
                else:
                    self.stdout.write(self.style.WARNING(f"Student {username} already exists, skipping."))

        self.stdout.write(self.style.SUCCESS(f"\nTotal students created/updated: {created_count}"))


