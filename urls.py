from django.urls import path
from . import views
from .views import student_profile
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [

    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', student_profile, name='student_profile'),
    path('skills/', views.skills_view, name='skills'),
    path('add-project/', views.add_project, name='add_project'),        # ← fixed name
    path('projects/', views.view_projects, name='projects'),             # ← fixed name
    path('delete-project/<int:project_id>/', views.delete_project, name='delete_project'),  # ← added
    path('learning-path/', views.learning_path, name='learning_path'),
    path('test/', views.test, name='test'),
    path('result/', views.result, name='result'),
    path('upload-resume/', views.upload_resume, name='upload_resume'),
    path('analyze-resume/', views.analyze_resume, name='analyze_resume'),
    path('companies/', views.company_list, name='companies'),
    path('jobs/', views.job_list, name='jobs'),
    path('generate-recommendations/', views.generate_recommendations, name='generate_recommendations'),
    path('recommendations/', views.recommendations_view, name='recommendations'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)