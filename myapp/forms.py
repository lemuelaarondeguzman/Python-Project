from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Survey, Question, Section, UserProfile, TemporaryPasswordCode

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    section = forms.ModelChoiceField(
        queryset=Section.objects.all(), 
        required=False, 
        empty_label="Select a section",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_section'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'section')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove help text from password fields
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        # Add form-control class to all fields if not already set
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.PasswordInput)):
                    field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        # No role validation needed - role will be set to 'student' by default in the view
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user

class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['title', 'description', 'open_time', 'due_date', 'time_limit_minutes']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter survey title...',
                'style': 'border: 2px solid #e5e7eb; border-radius: 8px; padding: 0.75rem 1rem; font-size: 1rem;'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Describe the purpose and instructions for this survey...',
                'style': 'border: 2px solid #e5e7eb; border-radius: 8px; padding: 0.75rem 1rem; font-size: 1rem; resize: vertical;'
            }),
            'open_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'style': 'border: 2px solid #e5e7eb; border-radius: 8px; padding: 0.75rem 1rem; font-size: 1rem;'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'style': 'border: 2px solid #e5e7eb; border-radius: 8px; padding: 0.75rem 1rem; font-size: 1rem;'
            }),
            'time_limit_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'e.g., 30',
                'style': 'border: 2px solid #e5e7eb; border-radius: 8px; padding: 0.75rem 1rem; font-size: 1rem;'
            }),
        }
    
    def clean_open_time(self):
        """
        Ensure open_time is properly timezone-aware for consistent comparison.
        datetime-local inputs are naive and represent local time (Philippine Time).
        Convert to timezone-aware datetime in Philippine timezone.
        Django automatically converts to UTC when saving (USE_TZ=True).
        """
        open_time = self.cleaned_data.get('open_time')
        if open_time:
            from django.utils import timezone
            
            # datetime-local inputs are naive (no timezone info)
            # They represent the time in Philippine timezone (Asia/Manila, UTC+8)
            if timezone.is_naive(open_time):
                # Get the default timezone from settings (Asia/Manila)
                # This interprets the naive datetime as Philippine time
                default_tz = timezone.get_default_timezone()
                
                # Make naive datetime timezone-aware in Philippine timezone
                # Django will automatically convert this to UTC when saving to database
                open_time = timezone.make_aware(open_time, default_tz)
            
        return open_time
    
    def clean_due_date(self):
        """
        Ensure due_date is properly timezone-aware for consistent comparison.
        datetime-local inputs are naive and represent local time (Philippine Time).
        Convert to timezone-aware datetime in Philippine timezone.
        Django automatically converts to UTC when saving (USE_TZ=True).
        """
        due_date = self.cleaned_data.get('due_date')
        if due_date:
            from django.utils import timezone
            
            # datetime-local inputs are naive (no timezone info)
            # They represent the time in Philippine timezone (Asia/Manila, UTC+8)
            if timezone.is_naive(due_date):
                # Get the default timezone from settings (Asia/Manila)
                # This interprets the naive datetime as Philippine time
                default_tz = timezone.get_default_timezone()
                
                # Make naive datetime timezone-aware in Philippine timezone
                # Django will automatically convert this to UTC when saving to database
                due_date = timezone.make_aware(due_date, default_tz)
            
            # If already timezone-aware, ensure it's using the correct timezone
            # Django will handle UTC conversion automatically when saving
            
        return due_date
    
    def clean(self):
        """
        Validate that open_time is before due_date if both are set.
        """
        cleaned_data = super().clean()
        open_time = cleaned_data.get('open_time')
        due_date = cleaned_data.get('due_date')
        
        if open_time and due_date:
            if open_time >= due_date:
                raise forms.ValidationError({
                    'open_time': 'Open time must be before the due date.'
                })
        
        return cleaned_data


class SurveyScheduleForm(SurveyForm):
    class Meta(SurveyForm.Meta):
        fields = ['open_time', 'due_date', 'time_limit_minutes']


class SurveyAssignmentForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['assigned_sections']
        widgets = {
            'assigned_sections': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'question_type', 'is_required']
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 2}),
        }

class ForgotPasswordForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username'
        }),
        label='Username'
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not User.objects.filter(username=username).exists():
            raise ValidationError('Username does not exist.')
        return username

class PasswordResetForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password'
        }),
        help_text="Password must be at least 8 characters long and contain at least one letter and one number."
    )
    new_password2 = forms.CharField(
        label="New password confirmation",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password'
        })
    )
    
    def clean_new_password1(self):
        password1 = self.cleaned_data.get('new_password1')
        if len(password1) < 8:
            raise ValidationError('Password must be at least 8 characters long.')
        if not any(char.isalpha() for char in password1):
            raise ValidationError('Password must contain at least one letter.')
        if not any(char.isdigit() for char in password1):
            raise ValidationError('Password must contain at least one number.')
        return password1

class StudentEditForm(forms.ModelForm):
    section = forms.ModelChoiceField(
        queryset=Section.objects.all(),
        required=False,
        empty_label="No section assigned",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['section'].initial = self.instance.profile.section
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and hasattr(user, 'profile'):
            user.profile.section = self.cleaned_data.get('section')
            user.profile.save()
        return user

class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'placeholder': 'Enter section name (e.g., BSIT 4E G1)'})
