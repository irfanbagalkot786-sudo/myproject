from .models import StudentProfile, Skill, StudentSkill

def profile_context(request):
    """
    Adds profile-related data to all template contexts.
    """
    if request.user.is_authenticated:
        student, _ = StudentProfile.objects.get_or_create(
            user=request.user,
            defaults={'full_name': request.user.username}
        )
        student_skills = StudentSkill.objects.filter(student=student).select_related('skill')
        all_skills = Skill.objects.all().order_by('category', 'name')
        
        return {
            'student': student,
            'student_skills': student_skills,
            'all_skills': all_skills,
        }
    return {}

