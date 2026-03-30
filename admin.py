from django.contrib import admin
from .models import StudentProfile,Skill, StudentSkill, LearningPath, Question, Assessment,Resume, ResumeAnalysis, Company, JobRole, Recommendation

class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'college', 'branch', 'cgpa', 'graduation_year')
from django.contrib import admin

admin.site.register(StudentProfile, StudentProfileAdmin)

admin.site.register(Skill)
admin.site.register(StudentSkill)
admin.site.register(LearningPath)
admin.site.register(Question)
admin.site.register(Assessment)
admin.site.register(Resume)
admin.site.register(ResumeAnalysis)
admin.site.register(Company)
admin.site.register(JobRole)
admin.site.register(Recommendation)