from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# ================= STUDENT PROFILE ===============

class StudentProfile(models.Model):

    BRANCH_CHOICES = [
        ('bca',   'BCA'),
        ('mca',   'MCA'),
        ('bba',   'BBA'),
        ('mba',   'MBA'),
        ('bcom',  'B.Com'),
        ('mcom',  'M.Com'),
        ('bsc',   'BSc'),
        ('other', 'Other'),
    ]

    WORK_MODE_CHOICES = [
        ('wfh',    'Work From Home'),
        ('office', 'Office'),
        ('hybrid', 'Hybrid'),
    ]

    user             = models.OneToOneField(User, on_delete=models.CASCADE)

    # Basic
    full_name        = models.CharField(max_length=200, blank=True, default='')
    college          = models.CharField(max_length=200, blank=True, default='')
    branch           = models.CharField(max_length=50, choices=BRANCH_CHOICES, blank=True, default='')
    cgpa             = models.FloatField(
                           validators=[MinValueValidator(0), MaxValueValidator(10)],
                           default=0, blank=True)
    graduation_year  = models.IntegerField(null=True, blank=True)
    phone            = models.CharField(max_length=15, blank=True, default='')

    # FIX 1: Added languages field (stored as comma-separated string)
    languages        = models.CharField(max_length=500, blank=True, default='')

    # Media
    profile_photo    = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    resume_file      = models.FileField(upload_to='resumes/', blank=True, null=True)

    # Bio & Links
    introduction     = models.TextField(blank=True, default='')
    linkedin_url     = models.URLField(blank=True, default='')
    github_url       = models.URLField(blank=True, default='')

    # Career
    work_mode        = models.CharField(
                           max_length=10, choices=WORK_MODE_CHOICES,
                           blank=True, null=True)
    placement_ready  = models.BooleanField(default=False)

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.username

    # FIX 2: helper to get languages as a Python list
    def get_languages_list(self):
        if self.languages:
            return [l.strip() for l in self.languages.split(',') if l.strip()]
        return []


# ================= STUDENT SKILLS =================

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

    languages = models.CharField(max_length=500, blank=True, default='')

    
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


    
# ================= ASSESSMENT =================

class Question(models.Model):
    QUESTION_TYPES = [
        ('aptitude',   'Aptitude'),
        ('technical',  'Technical'),
        # Infosys topics
        ('quantitative', 'Quantitative Aptitude'),
        ('logical',      'Logical Reasoning'),
        ('verbal',       'Verbal Ability'),
        ('arrays',       'Arrays'),
        ('strings',      'Strings'),
        ('sorting',      'Sorting Algorithms'),
        # TCS topics
        ('tcs_numerical',   'Numerical Ability'),
        ('tcs_verbal',      'Verbal Reasoning'),
        ('tcs_programming', 'Programming Logic'),
        ('tcs_coding',      'Coding'),
        ('tcs_data',        'Data Interpretation'),
    ]
 
    question_text  = models.TextField()
    option1        = models.CharField(max_length=200)
    option2        = models.CharField(max_length=200)
    option3        = models.CharField(max_length=200)
    option4        = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=200)
    category       = models.CharField(max_length=50, choices=QUESTION_TYPES)
 
    def __str__(self):
        return self.question_text
 
 
class Assessment(models.Model):
    student         = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    score           = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)
 
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

#================== COMPANY ================

class Company(models.Model):
    name            = models.CharField(max_length=200, unique=True)
    description     = models.TextField(blank=True)
    about_text      = models.TextField(blank=True)
    
    website         = models.URLField(blank=True)
    industry        = models.CharField(max_length=100, blank=True)
    
    # Stats
    employee_count  = models.CharField(max_length=50,  blank=True)
    countries_count = models.CharField(max_length=50,  blank=True)
    revenue         = models.CharField(max_length=100, blank=True)
    glassdoor_rating = models.FloatField(default=0.0)
    
    # UI/Branding
    logo_text       = models.CharField(max_length=10,  blank=True)
    banner_gradient = models.CharField(max_length=200, blank=True)
    
    created_at      = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return self.name


class CompanyTip(models.Model):
    company  = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='tips')
    tip_text = models.TextField()

    def __str__(self):
        return f"Tip for {self.company.name}"


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

    salary_range     = models.CharField(max_length=100, blank=True)
    location         = models.CharField(max_length=200, blank=True)
    
    # JSON Data (Stored as strings for simplicity)
    eligibility_json     = models.TextField(blank=True, help_text="JSON array of [key, value] pairs")
    interview_steps_json = models.TextField(blank=True, help_text="JSON array of {title, desc, tests: []} objects")

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


# ================= VIRTUAL INTERVIEW SESSION =================

class InterviewSession(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='interviews')
    company_name = models.CharField(max_length=200)
    video_file = models.FileField(upload_to='interviews/')
    
    # New Brain Features
    transcript   = models.TextField(blank=True, default='')
    ai_score     = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    ai_feedback  = models.TextField(blank=True, default='')
    strengths = models.TextField(blank=True, default="[]")
    weaknesses = models.TextField(blank=True, default="[]")

    confidence_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    eye_contact_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interview with {self.company_name} - {self.student.full_name}"
