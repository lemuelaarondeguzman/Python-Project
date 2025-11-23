from .models import Survey

def teacher_context(request):
    """
    Context processor to add teacher-specific data to all templates.
    """
    context = {}
    
    # Only add teacher context if user is authenticated and is a teacher
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.role == 'teacher':
            context['archived_surveys_count'] = Survey.objects.filter(
                created_by=request.user,
                is_archived=True
            ).count()
    
    return context

