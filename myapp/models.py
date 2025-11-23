from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class Section(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_sections')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): 
        return self.name

class SectionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='section_requests')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_requests')
    
    class Meta:
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.section.name} ({self.status})"

class Survey(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_surveys')
    assigned_sections = models.ManyToManyField(Section, related_name='surveys')
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False, help_text='Surveys remain hidden from students until published.')
    open_time = models.DateTimeField(null=True, blank=True, help_text="Time when the survey opens for students. If not set, survey opens immediately when published.")
    due_date = models.DateTimeField()
    is_archived = models.BooleanField(default=False, help_text='Archived surveys are hidden from students until restored.')
    time_limit_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Optional time limit (in minutes) for completing the survey.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        """
        Check if survey is currently open (active, past open_time if set, and not past due date).
        Real-time check: compares current time with open_time and due_date in UTC.
        Survey opens at open_time (if set) and closes when deadline is reached (now > due_date).
        """
        # Survey must be active
        if not self.is_active or not self.is_published:
            return False
        
        # Get current time (timezone-aware, in UTC when USE_TZ=True)
        now = timezone.now()
        
        # Check if survey has an open_time set and if current time is before it
        if self.open_time:
            open_time = self.open_time
            # Ensure open_time is timezone-aware
            if timezone.is_naive(open_time):
                from datetime import timezone as dt_timezone
                open_time = open_time.replace(tzinfo=dt_timezone.utc)
            
            # Survey is not open yet if current time is before open_time
            if now < open_time:
                return False
        
        # Get due_date from database (should be timezone-aware in UTC when USE_TZ=True)
        due_date = self.due_date
        
        # Ensure due_date is timezone-aware for proper comparison
        # With USE_TZ=True, due_date should already be timezone-aware in UTC
        # But handle edge case where it might be naive (shouldn't happen)
        if timezone.is_naive(due_date):
            from datetime import timezone as dt_timezone
            due_date = due_date.replace(tzinfo=dt_timezone.utc)
        
        # Real-time comparison: survey is open if current time is before or equal to due date
        # Survey closes when current time exceeds due date (now > due_date)
        # Both now and due_date are in UTC (Django stores all datetimes in UTC with USE_TZ=True)
        # This ensures real-time closing: surveys close immediately when deadline passes
        # Using <= (less than or equal) so surveys remain open until deadline passes
        return now <= due_date

class Question(models.Model):
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('likert_scale', 'Likert Scale'),
        ('short_answer', 'Short Answer'),
    ]

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    # For multiple choice questions
    choices = models.JSONField(default=list, blank=True)

    # For Likert scale questions
    likert_min = models.IntegerField(default=1)
    likert_max = models.IntegerField(default=5)
    likert_labels = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.survey.title} - {self.question_text[:50]}..."

    class Meta:
        ordering = ['order']

class Response(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='survey_responses')
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.survey.title}"

    class Meta:
        unique_together = ['survey', 'student']

class Answer(models.Model):
    response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True)
    answer_choice = models.CharField(max_length=100, blank=True)
    answer_number = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.response.student.username} - {self.question.question_text[:30]}..."

    class Meta:
        unique_together = ['response', 'question']

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    is_verified = models.BooleanField(default=True, help_text='Whether the student account has been verified by a teacher')

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class TemporaryPasswordCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='temp_password_codes')
    code = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.code} ({'Used' if self.used else 'Active'})"
    
    def is_valid(self):
        """Check if code is still valid (not used, not expired)"""
        if self.used:
            return False
        
        from datetime import timedelta
        expiry_time = self.created_at + timedelta(minutes=5)
        return timezone.now() <= expiry_time
    
    def mark_as_used(self):
        """Mark code as used"""
        self.used = True
        self.used_at = timezone.now()
        self.save()


class StudentSurveyProgress(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='progress_records')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='survey_progress')
    answers = models.JSONField(default=dict, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_submitted = models.BooleanField(default=False)

    class Meta:
        unique_together = ['survey', 'student']
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.student.username} progress on {self.survey.title}"

    def percent_complete(self):
        total_questions = self.survey.questions.count()
        if total_questions == 0:
            return 0
        answered = len([value for value in self.answers.values() if value not in (None, '', [])])
        return int((answered / total_questions) * 100)
