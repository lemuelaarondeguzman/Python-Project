from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import (
    Survey,
    Question,
    Response,
    Answer,
    Section,
    UserProfile,
    TemporaryPasswordCode,
    StudentSurveyProgress,
)
from .forms import (
    SurveyForm,
    QuestionForm,
    SurveyAssignmentForm,
    UserRegistrationForm,
    ForgotPasswordForm,
    PasswordResetForm,
    StudentEditForm,
    SectionForm,
    SurveyScheduleForm,
)
import json
import random
import string
from datetime import datetime, timedelta

def home(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile'):
            if request.user.profile.role == 'student':
                return redirect('student_dashboard')
            elif request.user.profile.role == 'teacher':
                return redirect('teacher_dashboard')
    return render(request, 'home.html')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            section = form.cleaned_data.get('section')
            
            # Default all registrations to 'student' role
            role = 'student'
            
            # Create profile with student role (auto-verified now)
            UserProfile.objects.create(
                user=user,
                role=role,
                section=section,
                is_verified=True
            )
            
            messages.success(request, 'Registration successful! You can now log in and start taking surveys.')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def student_dashboard(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Redirect to assigned surveys page
    return redirect('student_assigned_surveys')

@login_required
def student_assigned_surveys(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get all active surveys that haven't expired
    # Filter by section if user has a section assigned
    now = timezone.now()
    survey_filters = {
        'is_active': True,
        'is_published': True,
        'due_date__gte': now,
    }

    filters = {**survey_filters, 'is_archived': False}
    if request.user.profile.section:
        filters['assigned_sections'] = request.user.profile.section
        surveys = Survey.objects.filter(**filters).order_by('-created_at')
    else:
        surveys = Survey.objects.filter(**filters).order_by('-created_at')
    
    # Get surveys that the student has already responded to
    responses = Response.objects.filter(student=request.user)
    responded_survey_ids = set(responses.values_list('survey_id', flat=True))
    
    # Filter out completed surveys - only show surveys that haven't been answered yet
    surveys = surveys.exclude(id__in=responded_survey_ids)
    
    # Load progress records for visible surveys
    progress_records = StudentSurveyProgress.objects.filter(
        student=request.user,
        survey__in=surveys
    )
    progress_map = {record.survey_id: record for record in progress_records}
    
    # Check if there are any surveys available for the student to answer
    has_available_surveys = False
    for survey in surveys:
        if survey.is_open:
            has_available_surveys = True
        progress_record = progress_map.get(survey.id)
        if progress_record:
            total_questions = survey.questions.count()
            if total_questions:
                answered = len([value for value in progress_record.answers.values() if value not in ('', None)])
                survey.progress_percent = int((answered / total_questions) * 100)
            else:
                survey.progress_percent = 0
        else:
            survey.progress_percent = 0
    
    return render(request, 'student/assigned_surveys.html', {
        'surveys': surveys,
        'responded_survey_ids': set(),
        'has_available_surveys': has_available_surveys,
    })

@login_required
def student_response_history(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    responses = Response.objects.filter(student=request.user).order_by('-submitted_at')
    
    return render(request, 'student/response_history.html', {
        'responses': responses
    })

@login_required
def student_view_response_details(request, response_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'student':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    response = get_object_or_404(Response, id=response_id, student=request.user)
    answers = response.answers.all()
    
    # Convert submitted_at from UTC to local timezone
    local_submitted_at = timezone.localtime(response.submitted_at)
    
    details = {
        'survey': {
            'title': response.survey.title,
            'description': response.survey.description,
            'submitted_at': local_submitted_at.strftime('%B %d, %Y at %I:%M %p')
        },
        'answers': []
    }
    
    for answer in answers:
        answer_data = {
            'question': answer.question.question_text,
            'question_type': answer.question.get_question_type_display(),
            'answer': ''
        }
        
        if answer.question.question_type == 'multiple_choice':
            answer_data['answer'] = answer.answer_choice
        elif answer.question.question_type == 'likert_scale':
            answer_data['answer'] = str(answer.answer_number)
        elif answer.question.question_type == 'short_answer':
            answer_data['answer'] = answer.answer_text
        
        details['answers'].append(answer_data)
    
    return JsonResponse(details)


@login_required
@require_http_methods(["POST"])
def save_survey_progress(request, survey_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'student':
        return JsonResponse({'error': 'Access denied.'}, status=403)
    
    survey = get_object_or_404(Survey, id=survey_id)

    if not survey.is_open:
        return JsonResponse({'error': 'Survey is not open.'}, status=400)
    
    if request.user.profile.section and survey.assigned_sections.exists():
        if request.user.profile.section not in survey.assigned_sections.all():
            return JsonResponse({'error': 'Survey not assigned to your section.'}, status=400)
    
    if Response.objects.filter(survey=survey, student=request.user).exists():
        return JsonResponse({'error': 'Survey already submitted.'}, status=400)
    
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid payload.'}, status=400)
    
    answers = payload.get('answers', {})
    time_spent_seconds = int(payload.get('time_spent_seconds', 0))
    if time_spent_seconds < 0:
        time_spent_seconds = 0
    
    progress, _ = StudentSurveyProgress.objects.get_or_create(
        survey=survey,
        student=request.user,
        defaults={'answers': {}}
    )
    
    progress.answers = answers
    if time_spent_seconds > progress.time_spent_seconds:
        progress.time_spent_seconds = time_spent_seconds
    progress.is_submitted = False
    progress.save(update_fields=['answers', 'time_spent_seconds', 'is_submitted', 'updated_at'])
    
    time_limit_seconds = survey.time_limit_minutes * 60 if survey.time_limit_minutes else None
    remaining_seconds = None
    if time_limit_seconds is not None:
        remaining_seconds = max(time_limit_seconds - progress.time_spent_seconds, 0)
    
    return JsonResponse({
        'success': True,
        'remaining_seconds': remaining_seconds
    })


@login_required
def take_survey(request, survey_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    survey = get_object_or_404(Survey, id=survey_id)
    
    # Check if student has a section assigned
    if not request.user.profile.section:
        messages.error(request, 'You must be assigned to a section before you can take surveys. Please wait for your section request to be approved.')
        return redirect('student_dashboard')
    
    # Ensure survey has been published
    if not survey.is_published:
        messages.warning(request, 'This survey has not been published by your teacher yet.')
        return redirect('student_dashboard')

    # Check if survey is open
    if not survey.is_open:
        # Check if survey is scheduled to open later
        if survey.open_time and timezone.now() < survey.open_time:
            messages.warning(request, f'This survey is scheduled to open on {survey.open_time.strftime("%B %d, %Y at %I:%M %p")}. Please check back later.')
        else:
            messages.error(request, 'This survey is no longer available.')
        return redirect('student_dashboard')
    
    if Response.objects.filter(survey=survey, student=request.user).exists():
        messages.warning(request, 'You have already submitted this survey.')
        return redirect('student_dashboard')
    
    if request.user.profile.section and survey.assigned_sections.exists():
        if request.user.profile.section not in survey.assigned_sections.all():
            messages.error(request, 'This survey is not assigned to your section.')
            return redirect('student_dashboard')
    
    questions = survey.questions.all()
    progress, _ = StudentSurveyProgress.objects.get_or_create(
        survey=survey,
        student=request.user,
        defaults={'answers': {}}
    )
    saved_answers = progress.answers or {}
    saved_answers_json = json.dumps(saved_answers)
    question_ids = list(questions.values_list('id', flat=True))
    question_ids_json = json.dumps(question_ids)
    
    time_limit_seconds = survey.time_limit_minutes * 60 if survey.time_limit_minutes else None
    remaining_seconds = None
    if time_limit_seconds is not None:
        remaining_seconds = max(time_limit_seconds - progress.time_spent_seconds, 0)
        if remaining_seconds <= 0:
            messages.error(request, 'The time limit for this survey has been reached.')
            return redirect('student_response_history')
    
    if request.method == 'POST':
        # Double-check survey is still open before accepting submission
        # Refresh survey from database to get latest status
        survey.refresh_from_db()
        if not survey.is_open:
            messages.error(request, 'This survey is no longer available. The deadline has passed.')
            return redirect('student_dashboard')
        
        total_time_spent = progress.time_spent_seconds
        submitted_time_spent = int(request.POST.get('time_spent_seconds', total_time_spent))
        if submitted_time_spent < total_time_spent:
            submitted_time_spent = total_time_spent
        if time_limit_seconds is not None and submitted_time_spent > time_limit_seconds:
            messages.error(request, 'The time limit for this survey has been exceeded.')
            return redirect('student_assigned_surveys')
        
        progress.time_spent_seconds = submitted_time_spent
        progress.is_submitted = True
        progress.answers = {}
        progress.save(update_fields=['time_spent_seconds', 'is_submitted', 'answers', 'updated_at'])
        
        response = Response.objects.create(survey=survey, student=request.user)
        
        for question in questions:
            answer_value = request.POST.get(f'question_{question.id}')
            if answer_value:
                Answer.objects.create(
                    response=response,
                    question=question,
                    answer_text=answer_value if question.question_type == 'short_answer' else '',
                    answer_choice=answer_value if question.question_type == 'multiple_choice' else '',
                    answer_number=int(answer_value) if question.question_type == 'likert_scale' else None
                )
        
        messages.success(request, 'Survey submitted successfully!')
        progress.delete()
        return redirect('student_response_history')
    
    return render(request, 'student/take_survey.html', {
        'survey': survey,
        'questions': questions,
        'saved_answers': saved_answers,
        'time_limit_seconds': time_limit_seconds,
        'remaining_seconds': remaining_seconds,
        'progress_time_spent': progress.time_spent_seconds,
        'saved_answers_json': saved_answers_json,
        'question_ids_json': question_ids_json,
    })

@login_required
def teacher_dashboard(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    surveys_qs = Survey.objects.filter(created_by=request.user).order_by('-created_at')
    surveys = surveys_qs.filter(is_archived=False)
    total_responses = Response.objects.filter(survey__created_by=request.user).count()
    # Additional analytics data
    total_surveys = surveys.count()
    active_survey_list = [s for s in surveys if s.is_published and s.is_open]
    closed_surveys = [s for s in surveys if s.is_published and not s.is_open]
    draft_surveys = [s for s in surveys if not s.is_published and not s.is_archived]
    
    # Average responses per survey
    avg_responses_per_survey = total_responses / total_surveys if total_surveys > 0 else 0
    
    # Surveys with most responses
    surveys_with_counts = surveys.annotate(response_count=Count('responses')).order_by('-response_count')[:5]

    chart_ready_surveys = surveys.filter(is_archived=False).annotate(response_count=Count('responses')).order_by('-response_count')[:5]
    responses_chart_labels = [survey.title for survey in chart_ready_surveys]
    responses_chart_counts = [survey.response_count for survey in chart_ready_surveys]

    status_counts = {
        'Active': len([s for s in surveys if s.is_published and s.is_open]),
        'Closed': len([s for s in surveys if s.is_published and not s.is_open]),
        'Draft': len(draft_surveys),
    }
    
    # Collect text responses for word cloud
    text_responses = []
    short_answer_questions = Question.objects.filter(
        survey__created_by=request.user,
        question_type='short_answer'
    )
    for question in short_answer_questions:
        answers = Answer.objects.filter(
            question=question,
            answer_text__isnull=False
        ).exclude(answer_text='')
        text_responses.extend([answer.answer_text for answer in answers])
    
    return render(request, 'teacher/dashboard.html', {
        'surveys': surveys,
        'total_responses': total_responses,
        'total_surveys': total_surveys,
        'active_surveys': len(active_survey_list),
        'open_surveys_count': len(active_survey_list),
        'closed_surveys_count': len(closed_surveys),
        'avg_responses_per_survey': round(avg_responses_per_survey, 1),
        'surveys_with_counts': surveys_with_counts,
        'responses_chart_labels': json.dumps(responses_chart_labels),
        'responses_chart_counts': json.dumps(responses_chart_counts),
        'status_chart_labels': json.dumps(list(status_counts.keys())),
        'status_chart_data': json.dumps(list(status_counts.values())),
        'word_cloud_data': json.dumps(text_responses),
    })

@login_required
def manage_surveys(request):
    """Manage surveys - list all surveys with create/edit/delete functionality"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    surveys_queryset = Survey.objects.filter(created_by=request.user, is_archived=False).order_by('-created_at')
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip().lower()

    if search_query:
        surveys_queryset = surveys_queryset.filter(title__icontains=search_query)

    surveys = list(surveys_queryset)

    if status_filter == 'active':
        surveys = [s for s in surveys if s.is_published and s.is_open]
    elif status_filter == 'closed':
        surveys = [s for s in surveys if s.is_published and not s.is_open]
    elif status_filter == 'draft':
        surveys = [s for s in surveys if not s.is_published]
    
    return render(request, 'teacher/manage_surveys.html', {
        'surveys': surveys,
        'search_query': search_query,
        'status_filter': status_filter,
    })

@login_required
def archived_surveys(request):
    """View archived surveys"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    archived_surveys = Survey.objects.filter(created_by=request.user, is_archived=True).order_by('-updated_at')
    
    return render(request, 'teacher/archived_surveys.html', {
        'archived_surveys': archived_surveys,
    })

@login_required
def responses_overview(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    surveys = Survey.objects.filter(
        created_by=request.user,
        is_archived=False
    ).annotate(response_count=Count('responses')).order_by('-updated_at')
    
    search_query = request.GET.get('search', '').strip()
    if search_query:
        surveys = surveys.filter(title__icontains=search_query)
    
    status_filter = request.GET.get('status', '').strip().lower()
    if status_filter == 'active':
        surveys = [s for s in surveys if s.is_published and s.is_open]
    elif status_filter == 'draft':
        surveys = [s for s in surveys if not s.is_published]
    elif status_filter == 'closed':
        surveys = [s for s in surveys if s.is_published and not s.is_open]

    # Ensure iterable even after list comprehension
    if isinstance(surveys, list):
        filtered_surveys = surveys
    else:
        filtered_surveys = list(surveys)
    
    return render(request, 'teacher/responses_overview.html', {
        'surveys': filtered_surveys,
        'search_query': search_query,
        'status_filter': status_filter,
    })

@login_required
@require_http_methods(["POST"])
def publish_survey(request, survey_id):
    """Mark a survey as published so students can access it."""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')

    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)

    if survey.is_published:
        messages.info(request, 'This survey is already published.')
        return redirect('manage_surveys')

    if not survey.assigned_sections.exists():
        messages.error(request, 'Assign the survey to at least one section before publishing.')
        return redirect('edit_survey', survey_id=survey.id)

    survey.is_published = True
    survey.save(update_fields=['is_published', 'updated_at'])

    messages.success(request, 'Survey published! Students in the assigned sections can now see it.')
    return redirect('manage_surveys')

@login_required
@require_http_methods(["POST"])
def unpublish_survey(request, survey_id):
    """Unpublish a survey to hide it from students."""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')

    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)

    if not survey.is_published:
        messages.info(request, 'This survey is already unpublished.')
        return redirect('manage_surveys')

    survey.is_published = False
    survey.save(update_fields=['is_published', 'updated_at'])

    messages.success(request, 'Survey unpublished. Students can no longer access it.')
    return redirect('manage_surveys')

@login_required
@require_http_methods(["POST"])
def archive_survey(request, survey_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)
    
    if survey.is_archived:
        messages.info(request, 'Survey is already archived.')
        return redirect('manage_surveys')
    
    survey.is_archived = True
    survey.is_published = False
    survey.is_active = False
    survey.save(update_fields=['is_archived', 'is_published', 'is_active', 'updated_at'])
    
    messages.success(request, f'Survey "{survey.title}" archived. You can restore it anytime.')
    return redirect('manage_surveys')

@login_required
@require_http_methods(["POST"])
def restore_survey(request, survey_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)
    
    if not survey.is_archived:
        messages.info(request, 'Survey is not archived.')
        return redirect('manage_surveys')
    
    survey.is_archived = False
    survey.save(update_fields=['is_archived', 'updated_at'])
    
    messages.success(request, f'Survey "{survey.title}" restored. You can publish it again when ready.')
    return redirect('manage_surveys')

@login_required
def survey_builder(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    if request.method == 'POST':
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.created_by = request.user
            survey.save()
            form.save_m2m()  # Save many-to-many relationships (assigned_sections)
            return redirect('edit_survey', survey_id=survey.id)
    else:
        form = SurveyForm()
    
    return render(request, 'teacher/survey_builder.html', {
        'form': form
    })

@login_required
def edit_survey(request, survey_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)
    questions = survey.questions.all()
    assignment_form = SurveyAssignmentForm(instance=survey)
    schedule_form = SurveyScheduleForm(instance=survey)
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'question')
        
        if form_type == 'assignment':
            assignment_form = SurveyAssignmentForm(request.POST, instance=survey)
            if assignment_form.is_valid():
                assignment_form.save()
                if survey.is_published and not survey.assigned_sections.exists():
                    survey.is_published = False
                    survey.save(update_fields=['is_published', 'updated_at'])
                    messages.info(request, 'Survey was unpublished because no sections are assigned.')
                else:
                    messages.success(request, 'Sections updated successfully.')
                return redirect('edit_survey', survey_id=survey_id)
        elif form_type == 'schedule':
            schedule_form = SurveyScheduleForm(request.POST, instance=survey)
            if schedule_form.is_valid():
                schedule_form.save()
                messages.success(request, 'Schedule updated successfully.')
                return redirect('edit_survey', survey_id=survey_id)
        else:
            question_text = request.POST.get('question_text')
            question_type = request.POST.get('question_type')
            is_required = request.POST.get('is_required') == 'on'
            
            if question_text and question_type:
                question = Question.objects.create(
                    survey=survey,
                    question_text=question_text,
                    question_type=question_type,
                    is_required=is_required,
                    order=questions.count()
                )
                
                if question_type == 'multiple_choice':
                    choices_text = request.POST.get('choices', '')
                    if choices_text:
                        choices = [choice.strip() for choice in choices_text.split('\n') if choice.strip()]
                        question.choices = choices
                        question.save()
                
                elif question_type == 'likert_scale':
                    likert_min = request.POST.get('likert_min', 1)
                    likert_max = request.POST.get('likert_max', 5)
                    likert_labels_text = request.POST.get('likert_labels', '')
                    
                    question.likert_min = int(likert_min)
                    question.likert_max = int(likert_max)
                    
                    if likert_labels_text:
                        labels = [label.strip() for label in likert_labels_text.split('\n') if label.strip()]
                        question.likert_labels = labels
                    
                    question.save()
                
                messages.success(request, 'Question added successfully!')
                return redirect('edit_survey', survey_id=survey_id)
    
    return render(request, 'teacher/edit_survey.html', {
        'survey': survey,
        'questions': questions,
        'assignment_form': assignment_form,
        'schedule_form': schedule_form,
    })

@login_required
def response_management(request, survey_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)
    responses = Response.objects.filter(survey=survey).order_by('-submitted_at')
    
    search_query = request.GET.get('search')
    if search_query:
        responses = responses.filter(
            Q(student__username__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query)
        )
    
    selected_date = request.GET.get('submitted_date')
    if selected_date:
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
            responses = responses.filter(submitted_at__date=date_obj)
        except ValueError:
            messages.warning(request, 'Invalid date filter removed. Showing all responses.')
            selected_date = None
    
    paginator = Paginator(responses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'teacher/response_management.html', {
        'survey': survey,
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_date': selected_date
    })

@login_required
def analytics(request, survey_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)
    questions = survey.questions.all()
    
    analytics_data = {}
    for question in questions:
        answers = Answer.objects.filter(question=question)
        
        if question.question_type == 'multiple_choice':
            choice_counts = {}
            for answer in answers:
                choice = answer.answer_choice
                choice_counts[choice] = choice_counts.get(choice, 0) + 1
            analytics_data[question.id] = {
                'type': 'multiple_choice',
                'data': choice_counts
            }
        
        elif question.question_type == 'likert_scale':
            likert_counts = {}
            for answer in answers:
                value = answer.answer_number
                if value:
                    likert_counts[value] = likert_counts.get(value, 0) + 1
            analytics_data[question.id] = {
                'type': 'likert_scale',
                'data': likert_counts,
                'likert_labels': question.likert_labels if question.likert_labels else [],
                'likert_min': question.likert_min,
                'likert_max': question.likert_max
            }
        
        elif question.question_type == 'short_answer':
            text_responses = [answer.answer_text for answer in answers if answer.answer_text]
            analytics_data[question.id] = {
                'type': 'short_answer',
                'data': text_responses
            }
    
    import json
    
    print("Analytics Data:", analytics_data)
    
    return render(request, 'teacher/analytics.html', {
        'survey': survey,
        'questions': questions,
        'analytics_data': json.dumps(analytics_data)
    })

@login_required
def view_response_details(request, response_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    response = get_object_or_404(Response, id=response_id, survey__created_by=request.user)
    answers = response.answers.all()
    
    # Convert submitted_at from UTC to local timezone (Philippine Time)
    local_submitted_at = timezone.localtime(response.submitted_at)
    
    details = {
        'student': {
            'name': f"{response.student.first_name} {response.student.last_name}",
            'username': response.student.username,
            'email': response.student.email
        },
        'survey': {
            'title': response.survey.title,
            'submitted_at': local_submitted_at.strftime('%B %d, %Y at %I:%M %p')
        },
        'answers': []
    }
    
    for answer in answers:
        answer_data = {
            'question': answer.question.question_text,
            'question_type': answer.question.get_question_type_display(),
            'answer': ''
        }
        
        if answer.question.question_type == 'multiple_choice':
            answer_data['answer'] = answer.answer_choice
        elif answer.question.question_type == 'likert_scale':
            answer_data['answer'] = str(answer.answer_number)
        elif answer.question.question_type == 'short_answer':
            answer_data['answer'] = answer.answer_text
        
        details['answers'].append(answer_data)
    
    return JsonResponse(details)

@login_required
def edit_question(request, question_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    question = get_object_or_404(Question, id=question_id, survey__created_by=request.user)
    
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        question_type = request.POST.get('question_type')
        is_required = request.POST.get('is_required') == 'on'
        
        if question_text and question_type:
            question.question_text = question_text
            question.question_type = question_type
            question.is_required = is_required
            
            # Handle multiple choice options
            if question_type == 'multiple_choice':
                choices_text = request.POST.get('choices', '')
                if choices_text:
                    choices = [choice.strip() for choice in choices_text.split('\n') if choice.strip()]
                    question.choices = choices
                else:
                    question.choices = []
            
            # Handle Likert scale options
            elif question_type == 'likert_scale':
                likert_min = request.POST.get('likert_min', 1)
                likert_max = request.POST.get('likert_max', 5)
                likert_labels_text = request.POST.get('likert_labels', '')
                
                question.likert_min = int(likert_min)
                question.likert_max = int(likert_max)
                
                if likert_labels_text:
                    labels = [label.strip() for label in likert_labels_text.split('\n') if label.strip()]
                    question.likert_labels = labels
                else:
                    question.likert_labels = []
            
            question.save()
            
            return JsonResponse({'success': True, 'message': 'Question updated successfully!'})
        else:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def delete_question(request, question_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    question = get_object_or_404(Question, id=question_id, survey__created_by=request.user)
    survey_id = question.survey.id
    question.delete()
    
    return JsonResponse({'success': True, 'survey_id': survey_id})

@login_required
def reorder_questions(request, survey_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)
    
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            question_orders = data.get('question_orders', [])
            
            # Update order for each question
            for item in question_orders:
                question_id = item.get('id')
                new_order = item.get('order')
                
                if question_id and new_order is not None:
                    question = Question.objects.get(id=question_id, survey=survey)
                    question.order = new_order
                    question.save()
            
            return JsonResponse({'success': True, 'message': 'Question order updated successfully!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def delete_survey(request, survey_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)
    
    if not survey.is_archived:
        messages.error(request, 'Archive the survey first before deleting permanently.')
        return redirect('manage_surveys')
    
    if request.method == 'POST':
        survey_title = survey.title
        survey.delete()
        messages.success(request, f'Survey "{survey_title}" has been deleted successfully.')
        return redirect('manage_surveys')
    
    return render(request, 'teacher/delete_survey_confirm.html', {
        'survey': survey
    })

@login_required
def manage_sections(request):
    """Manage sections - list all sections with create/edit/delete functionality"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get all sections
    sections = Section.objects.all().order_by('name')
    
    # For each section, get student count
    sections_with_counts = []
    for section in sections:
        student_count = UserProfile.objects.filter(section=section, role='student').count()
        sections_with_counts.append({
            'section': section,
            'student_count': student_count
        })
    
    return render(request, 'teacher/manage_sections.html', {
        'sections_with_counts': sections_with_counts
    })

@login_required
def create_section(request):
    """Create a new section"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    if request.method == 'POST':
        form = SectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.created_by = request.user
            section.save()
            messages.success(request, f'Section "{section.name}" created successfully!')
            return redirect('manage_sections')
    else:
        form = SectionForm()
    
    return render(request, 'teacher/create_section.html', {
        'form': form
    })

@login_required
def edit_section(request, section_id):
    """Edit a section"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    section = get_object_or_404(Section, id=section_id)
    
    if request.method == 'POST':
        form = SectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, f'Section "{section.name}" updated successfully!')
            return redirect('manage_sections')
    else:
        form = SectionForm(instance=section)
    
    # Get student count for this section
    student_count = UserProfile.objects.filter(section=section, role='student').count()
    
    return render(request, 'teacher/edit_section.html', {
        'form': form,
        'section': section,
        'student_count': student_count
    })

@login_required
def delete_section(request, section_id):
    """Delete a section"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    section = get_object_or_404(Section, id=section_id)
    
    if request.method == 'POST':
        section_name = section.name
        student_count = UserProfile.objects.filter(section=section, role='student').count()
        
        # Check if section has students assigned
        if student_count > 0:
            messages.error(request, f'Cannot delete section "{section_name}" because it has {student_count} student(s) assigned. Please reassign or remove students first.')
            return redirect('manage_sections')
        
        # Check if section is assigned to any surveys
        survey_count = section.surveys.count()
        if survey_count > 0:
            messages.error(request, f'Cannot delete section "{section_name}" because it is assigned to {survey_count} survey(s). Please remove the section from surveys first.')
            return redirect('manage_sections')
        
        section.delete()
        messages.success(request, f'Section "{section_name}" deleted successfully!')
        return redirect('manage_sections')
    
    # Get counts for confirmation page
    student_count = UserProfile.objects.filter(section=section, role='student').count()
    survey_count = section.surveys.count()
    
    return render(request, 'teacher/delete_section_confirm.html', {
        'section': section,
        'student_count': student_count,
        'survey_count': survey_count
    })

@login_required
def teacher_settings(request):
    """Settings page for teachers - main settings hub"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    return render(request, 'teacher/settings.html')

@login_required
def set_due_dates(request):
    """Set due dates for surveys"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get all surveys created by the teacher
    surveys = Survey.objects.filter(created_by=request.user).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        surveys = surveys.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'published':
        surveys = surveys.filter(is_published=True, is_archived=False)
    elif status_filter == 'unpublished':
        surveys = surveys.filter(is_published=False, is_archived=False)
    elif status_filter == 'archived':
        surveys = surveys.filter(is_archived=True)
    
    return render(request, 'teacher/set_due_dates.html', {
        'surveys': surveys,
        'search_query': search_query,
        'status_filter': status_filter,
        'current_time': timezone.now(),
    })

@login_required
def update_survey_due_date(request, survey_id):
    """Update due date for a specific survey"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)
    
    if request.method == 'POST':
        form = SurveyScheduleForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            messages.success(request, f'Due date for "{survey.title}" updated successfully!')
            return redirect('set_due_dates')
    else:
        form = SurveyScheduleForm(instance=survey)
    
    return render(request, 'teacher/update_due_date.html', {
        'form': form,
        'survey': survey
    })


def generate_temp_code():
    """Generate a random 6-digit code"""
    return ''.join(random.choices(string.digits, k=6))

def forgot_password(request):
    """Handle forgot password request - generate temporary code"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            user = User.objects.get(username=username)
            
            # Clean up expired codes (older than 5 minutes)
            expiry_threshold = timezone.now() - timedelta(minutes=5)
            TemporaryPasswordCode.objects.filter(
                created_at__lt=expiry_threshold,
                used=False
            ).delete()
            
            # Generate unique code
            code = generate_temp_code()
            while TemporaryPasswordCode.objects.filter(code=code, used=False).exists():
                code = generate_temp_code()
            
            # Delete any existing unused codes for this user (invalidate old codes)
            TemporaryPasswordCode.objects.filter(user=user, used=False).delete()
            
            # Create new temporary code
            temp_code = TemporaryPasswordCode.objects.create(user=user, code=code)
            
            # Store code in session to display
            request.session['temp_code'] = code
            request.session['temp_code_user_id'] = user.id
            
            return redirect('forgot_password_code')
    else:
        form = ForgotPasswordForm()
    
    return render(request, 'registration/forgot_password.html', {'form': form})

def forgot_password_code(request):
    """Display the generated temporary code"""
    if request.user.is_authenticated:
        return redirect('home')
    
    code = request.session.get('temp_code')
    user_id = request.session.get('temp_code_user_id')
    
    if not code or not user_id:
        messages.error(request, 'No temporary code found. Please request a new one.')
        return redirect('forgot_password')
    
    user = get_object_or_404(User, id=user_id)
    
    # Verify code exists and is valid
    temp_code_obj = TemporaryPasswordCode.objects.filter(
        user=user, 
        code=code, 
        used=False
    ).first()
    
    if not temp_code_obj or not temp_code_obj.is_valid():
        messages.error(request, 'Code has expired. Please request a new one.')
        return redirect('forgot_password')
    
    context = {
        'code': code,
        'username': user.username
    }
    
    return render(request, 'registration/forgot_password_code.html', context)

class CustomLoginView(LoginView):
    """Custom login view that accepts both password and temporary codes"""
    template_name = 'home.html'
    
    def check_student_verification(self, user):
        """Verification no longer required; allow all student logins."""
        return True, None
    
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Check if password is a temporary code (6 digits)
        if password and len(password) == 6 and password.isdigit():
            # Try to authenticate with temporary code
            temp_code = TemporaryPasswordCode.objects.filter(
                code=password,
                used=False
            ).first()
            
            if temp_code and temp_code.is_valid():
                user = temp_code.user
                # Verify username matches the code's user
                if user.username != username:
                    messages.error(request, 'Username does not match the temporary code.')
                    return self.form_invalid(self.get_form())
                
                # Check if student account is verified
                is_verified, error_message = self.check_student_verification(user)
                if not is_verified:
                    messages.error(request, error_message)
                    return self.form_invalid(self.get_form())
                
                # Delete the code after use (single use requirement)
                temp_code.delete()
                # Login user
                login(request, user)
                # Set flag in session to force password change
                request.session['force_password_change'] = True
                messages.success(request, 'Logged in with temporary code. Please set a new password.')
                return redirect('force_password_change')
            else:
                messages.error(request, 'Invalid or expired temporary code.')
                return self.form_invalid(self.get_form())
        
        # Regular password authentication - override form_valid to check pending request
        form = self.get_form()
        if form.is_valid():
            user = form.get_user()
            
            # Check if student account is verified
            is_verified, error_message = self.check_student_verification(user)
            if not is_verified:
                messages.error(request, error_message)
                return self.form_invalid(form)
            
            # If no pending request, proceed with normal login
            login(request, user)
            return redirect(self.get_success_url())
        
        return self.form_invalid(form)

@login_required
def force_password_change(request):
    """Force user to change password after using temporary code"""
    if not request.session.get('force_password_change'):
        return redirect('home')
    
    if request.method == 'POST':
        form = PasswordResetForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Clear the flag
            request.session.pop('force_password_change', None)
            messages.success(request, 'Password changed successfully!')
            
            # Redirect based on user role
            if hasattr(request.user, 'profile'):
                if request.user.profile.role == 'student':
                    return redirect('student_dashboard')
                elif request.user.profile.role == 'teacher':
                    return redirect('teacher_dashboard')
            return redirect('home')
    else:
        form = PasswordResetForm(user=request.user)
    
    return render(request, 'registration/force_password_change.html', {'form': form})

@login_required
def manage_students(request):
    """List all sections for teacher management with pagination"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get all sections with student counts
    sections_query = Section.objects.annotate(
        student_count=Count('students', filter=Q(students__role='student'))
    ).order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        sections_query = sections_query.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Paginate sections (10 per page)
    paginator = Paginator(sections_query, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get all sections for statistics
    all_sections = Section.objects.all()
    
    # Statistics
    all_students = User.objects.filter(profile__role='student')
    total_students = all_students.count()
    active_students = all_students.filter(is_active=True).count()
    inactive_students = total_students - active_students
    
    return render(request, 'teacher/manage_students.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_students': total_students,
        'active_students': active_students,
        'inactive_students': inactive_students,
    })

@login_required
def edit_student(request, student_id):
    """Edit student information"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    student = get_object_or_404(User, id=student_id, profile__role='student')
    
    if request.method == 'POST':
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f'Student {student.get_full_name() or student.username} updated successfully.')
            return redirect('manage_students')
    else:
        form = StudentEditForm(instance=student)
    
    return render(request, 'teacher/edit_student.html', {
        'form': form,
        'student': student
    })

@login_required
def toggle_student_access(request, student_id):
    """Toggle student access (block/unblock)"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    student = get_object_or_404(User, id=student_id, profile__role='student')
    
    if request.method == 'POST':
        student.is_active = not student.is_active
        student.save()
        
        status = 'activated' if student.is_active else 'marked inactive'
        messages.success(request, f'Student {student.get_full_name() or student.username} has been {status}.')
    
    return redirect('manage_students')

@login_required
def section_students(request, section_id):
    """Get paginated list of students in a section"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
        return JsonResponse({'error': 'Access denied.'}, status=403)
    
    section = get_object_or_404(Section, id=section_id)
    
    # Get students in this section
    students = User.objects.filter(
        profile__role='student',
        profile__section=section
    ).select_related('profile').order_by('first_name', 'last_name', 'username')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        students = students.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        students = students.filter(is_active=True)
    elif status_filter == 'inactive':
        students = students.filter(is_active=False)
    
    # Paginate students (10 per page)
    paginator = Paginator(students, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Prepare response data
    students_data = []
    for student in page_obj:
        students_data.append({
            'id': student.id,
            'name': f'{student.first_name} {student.last_name}'.strip() or student.username,
            'username': student.username,
            'email': student.email,
            'status': 'active' if student.is_active else 'inactive',
            'date_joined': student.date_joined.strftime('%b %d, %Y'),
        })
    
    return JsonResponse({
        'section': {
            'id': section.id,
            'name': section.name,
            'description': section.description or '',
        },
        'students': students_data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'total_count': paginator.count,
        },
        'search_query': search_query,
        'status_filter': status_filter,
    })
