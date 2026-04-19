from django.urls import path
from . import views 
from .views import student_profile
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

urlpatterns = [

    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.student_profile, name='student_profile'),
    path('skills/', views.skills_view, name='skills'),
    path('add-custom-skill/', views.add_custom_skill, name='add_custom_skill'),
    path('delete-custom-skill/<int:skill_id>/', views.delete_custom_skill, name='delete_custom_skill'),
    path('add-project/', views.add_project, name='add_project'),        
    path('projects/', views.view_projects, name='projects'),             
    path('delete-project/<int:project_id>/', views.delete_project, name='delete_project'),  
    path('test/', views.test, name='test'),
    path('result/', views.result, name='result'),
    path('save-assessment/', views.save_assessment, name='save_assessment'),
    path('upload-resume/', views.upload_resume, name='upload_resume'),
    path('analyze-resume/', views.analyze_resume, name='analyze_resume'),
    path('companies/', views.company_list, name='companies'),
    path('jobs/', views.job_list, name='jobs'),
    path('generate-recommendations/', views.generate_recommendations, name='generate_recommendations'),
    path('recommendations/', views.recommendations_view, name='recommendations'),
    path('virtual-interview/', views.virtual_interview, name='virtual_interview'),
    path('save-interview/', views.save_interview, name='save_interview'),
    path('interview-results/', views.interview_results, name='interview_results'),
    path('generate-tech-questions/', views.generate_tech_questions, name='generate_tech_questions'),
    path('interview-detail/<int:interview_id>/', views.interview_detail, name='interview_detail'),
    path('process/<int:interview_id>/', views.process_interview, name='process_interview'),
    path('delete-interview/<int:interview_id>/', views.delete_interview, name='delete_interview'),
    path('logout/', views.logout_view, name='logout'),
    path('remove-photo/', views.remove_photo, name='remove_photo'),
    path('update-photo/', views.update_photo, name='update_photo'),
    path('delete-skill/<int:skill_id>/', views.delete_skill, name='delete_skill'),
    path('generate-ai-questions/', views.generate_ai_questions, name='generate_ai_questions'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
