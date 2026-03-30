from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# ================= STUDENT PROFILE =================

class StudentProfile(models.Model):

    BRANCH_CHOICES = [
        ('bca', 'BCA'),
        ('mca', 'MCA'),
        ('bba', 'BBA'),
        ('mba', 'MBA'),
        ('bcom', 'B.Com'),
        ('mcom', 'M.Com'),
        ('bsc', 'BSc'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=200)
    college = models.CharField(max_length=200, blank=True)
    branch = models.CharField(max_length=50, choices=BRANCH_CHOICES, blank=True)

    cgpa = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)], default=0)
    graduation_year = models.IntegerField(null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)

    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    resume_file = models.FileField(upload_to='resumes/', blank=True)

    introduction = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)

    placement_ready = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name


    # ================= SKILLS =================


class Skill(models.Model):

    CATEGORY_CHOICES = [
        ('technical', 'Technical'),
        ('soft', 'Soft Skills'),
        ('tool', 'Tool'),
        ('language', 'Language'),
        ('aptitude', 'Aptitude'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES,default='technical')

    def __str__(self):
        return f"{self.name} ({self.category})"


# ================= STUDENT SKILLS =================

class StudentSkill(models.Model):

    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    is_in_demand = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.full_name} - {self.skill.name}"
    

#=============projects===============

class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    github_link = models.URLField()

    def __str__(self):
        return self.title

# ================= LEARNING PATH =================

class LearningPath(models.Model):

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)
    description = models.TextField()

    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.title}"
    
# ================= ASSESSMENT =================

class Question(models.Model):

    QUESTION_TYPES = [
        ('aptitude', 'Aptitude'),
        ('technical', 'Technical'),
    ]

    question_text = models.TextField()
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200)
    option4 = models.CharField(max_length=200)

    correct_answer = models.CharField(max_length=200)

    category = models.CharField(max_length=50, choices=QUESTION_TYPES)

    def __str__(self):
        return self.question_text


class Assessment(models.Model):

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)

    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.score}"

# ================= RESUME =================

class Resume(models.Model):

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='resumes')

    file = models.FileField(upload_to='resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.full_name} Resume"


# ================= RESUME ANALYSIS =================

class ResumeAnalysis(models.Model):

    resume = models.OneToOneField(Resume, on_delete=models.CASCADE, related_name='analysis')

    extracted_skills = models.ManyToManyField(Skill, blank=True)

    experience_years = models.FloatField(default=0)

    projects = models.TextField(blank=True)
    certifications = models.TextField(blank=True)

    analysis_score = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    feedback = models.TextField(blank=True)

    analyzed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.resume.student.full_name} - {self.analysis_score}%"

#================== COMPANY =================
class Company(models.Model):

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ================= JOB ROLE =================

class JobRole(models.Model):

    EXPERIENCE_LEVEL = [
        ('entry', 'Entry Level'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior Level'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    required_skills = models.ManyToManyField(Skill)
    preferred_skills = models.ManyToManyField(Skill, blank=True, related_name='preferred_jobs')

    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVEL)

    min_cgpa = models.FloatField(default=0)

    salary_range = models.CharField(max_length=100, blank=True)

    location = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company.name} - {self.title}"


# ================= RECOMMENDATION ================

class Recommendation(models.Model):

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE)

    match_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    matching_skills = models.ManyToManyField(Skill, blank=True)
    missing_skills = models.ManyToManyField(Skill, related_name='missing_skills', blank=True)

    recommendation_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.job_role.title} ({self.match_percentage}%)"
