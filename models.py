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

    full_name        = models.CharField(max_length=200, blank=True, default='')
    college          = models.CharField(max_length=200, blank=True, default='')
    branch           = models.CharField(max_length=50, choices=BRANCH_CHOICES, blank=True, default='')
    cgpa             = models.FloatField(
                           validators=[MinValueValidator(0), MaxValueValidator(10)],
                           default=0, blank=True)
    graduation_year  = models.IntegerField(null=True, blank=True)
    phone            = models.CharField(max_length=15, blank=True, default='')
    languages        = models.CharField(max_length=500, blank=True, default='')

    profile_photo    = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    resume_file      = models.FileField(upload_to='resumes/', blank=True, null=True)

    introduction     = models.TextField(blank=True, default='')
    linkedin_url     = models.URLField(blank=True, default='')
    github_url       = models.URLField(blank=True, default='')

    work_mode        = models.CharField(
                           max_length=10, choices=WORK_MODE_CHOICES,
                           blank=True, null=True)
    job_role         = models.CharField(max_length=200, blank=True, default='')
    placement_ready  = models.BooleanField(default=False)

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.username

    def get_languages_list(self):
        if self.languages:
            return [l.strip() for l in self.languages.split(',') if l.strip()]
        return []


# ================= SKILL (kept for resume analysis / recommendations) =================

class Skill(models.Model):

    CATEGORY_CHOICES = [
        ('technical', 'Technical'),
        ('soft', 'Soft Skills'),
        ('tool', 'Tool'),
        ('language', 'Language'),
        ('aptitude', 'Aptitude'),
    ]

    name     = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='technical')

    def __str__(self):
        return f"{self.name} ({self.category})"


class StudentSkill(models.Model):
    """Legacy model kept for resume analysis extracted skills."""

    LEVEL_CHOICES = [
        ('beginner',     'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced',     'Advanced'),
    ]

    student      = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    skill        = models.ForeignKey(Skill, on_delete=models.CASCADE)
    level        = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True, default='beginner')
    is_in_demand = models.BooleanField(default=False)
    languages    = models.CharField(max_length=500, blank=True, default='')

    def __str__(self):
        return f"{self.student.full_name} - {self.skill.name}"


# ================= CUSTOM SKILL (student-defined, free-form) =================

class CustomSkill(models.Model):
    """
    Skills that students add themselves by typing a name and picking a level 1–5.
    Not tied to any pre-seeded Skill table.
    """
    student    = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='custom_skills')
    skill_name = models.CharField(max_length=100)
    level      = models.PositiveSmallIntegerField(
                     validators=[MinValueValidator(1), MaxValueValidator(5)],
                     default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['skill_name']
        unique_together = ('student', 'skill_name')   # prevent exact duplicates per student

    def __str__(self):
        return f"{self.student.full_name} — {self.skill_name} (Level {self.level})"

    def level_label(self):
        labels = {1: 'Beginner', 2: 'Elementary', 3: 'Intermediate', 4: 'Advanced', 5: 'Expert'}
        return labels.get(self.level, 'Unknown')

    def level_color(self):
        colors = {
            1: ('rgba(251,191,36,0.12)', '#b45309', 'rgba(251,191,36,0.35)'),
            2: ('rgba(251,191,36,0.18)', '#d97706', 'rgba(251,191,36,0.4)'),
            3: ('rgba(10,163,181,0.12)', '#088a9a', 'rgba(10,163,181,0.28)'),
            4: ('rgba(16,185,129,0.10)', '#065f46', 'rgba(16,185,129,0.30)'),
            5: ('rgba(139,92,246,0.10)', '#5b21b6', 'rgba(139,92,246,0.28)'),
        }
        return colors.get(self.level, colors[1])


# ================= PROJECT =================

class Project(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    title       = models.CharField(max_length=200)
    description = models.TextField()
    github_link = models.URLField()

    def __str__(self):
        return self.title


# ================= ASSESSMENT =================

class Question(models.Model):
    QUESTION_TYPES = [
        ('aptitude',        'Aptitude'),
        ('technical',       'Technical'),
        ('quantitative',    'Quantitative Aptitude'),
        ('logical',         'Logical Reasoning'),
        ('verbal',          'Verbal Ability'),
        ('arrays',          'Arrays'),
        ('strings',         'Strings'),
        ('sorting',         'Sorting Algorithms'),
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
    student     = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='resumes')
    file        = models.FileField(upload_to='resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.full_name} Resume"


# ================= RESUME ANALYSIS =================

class ResumeAnalysis(models.Model):
    resume           = models.OneToOneField('Resume', on_delete=models.CASCADE)
    analysis_score   = models.IntegerField(default=0)
    experience_years = models.FloatField(default=0)
    feedback         = models.TextField(blank=True)

    ats_score        = models.IntegerField(default=0)
    summary          = models.TextField(blank=True)
    strong_points    = models.JSONField(default=list, blank=True)
    weak_points      = models.JSONField(default=list, blank=True)
    skills_present   = models.JSONField(default=list, blank=True)
    skills_missing   = models.JSONField(default=list, blank=True)
    ats_keywords     = models.JSONField(default=list, blank=True)
    pro_tips         = models.JSONField(default=list, blank=True)

    extracted_skills = models.ManyToManyField('Skill', blank=True)

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analysis for {self.resume} — Score: {self.analysis_score}"


# ================= COMPANY =================

class Company(models.Model):
    name             = models.CharField(max_length=200, unique=True)
    description      = models.TextField(blank=True)
    about_text       = models.TextField(blank=True)
    website          = models.URLField(blank=True)
    industry         = models.CharField(max_length=100, blank=True)
    employee_count   = models.CharField(max_length=50,  blank=True)
    countries_count  = models.CharField(max_length=50,  blank=True)
    revenue          = models.CharField(max_length=100, blank=True)
    glassdoor_rating = models.FloatField(default=0.0)
    logo_text        = models.CharField(max_length=10,  blank=True)
    banner_gradient  = models.CharField(max_length=200, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

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
        ('entry',  'Entry Level'),
        ('mid',    'Mid Level'),
        ('senior', 'Senior Level'),
    ]

    company          = models.ForeignKey(Company, on_delete=models.CASCADE)
    title            = models.CharField(max_length=200)
    description      = models.TextField(blank=True)
    required_skills  = models.ManyToManyField(Skill)
    preferred_skills = models.ManyToManyField(Skill, blank=True, related_name='preferred_jobs')
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVEL)
    min_cgpa         = models.FloatField(default=0)
    salary_range     = models.CharField(max_length=100, blank=True)
    location         = models.CharField(max_length=200, blank=True)
    eligibility_json     = models.TextField(blank=True)
    interview_steps_json = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company.name} - {self.title}"


# ================= RECOMMENDATION =================

class Recommendation(models.Model):
    student              = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    job_role             = models.ForeignKey(JobRole, on_delete=models.CASCADE)
    match_percentage     = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    matching_skills      = models.ManyToManyField(Skill, blank=True)
    missing_skills       = models.ManyToManyField(Skill, related_name='missing_skills', blank=True)
    recommendation_reason = models.TextField(blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.job_role.title} ({self.match_percentage}%)"


# ================= VIRTUAL INTERVIEW SESSION =================

class InterviewSession(models.Model):
    student           = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='interviews')
    company_name      = models.CharField(max_length=200)
    video_file        = models.FileField(upload_to='interviews/')
    transcript        = models.TextField(blank=True, default='')
    ai_score          = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    ai_feedback       = models.TextField(blank=True, default='')
    strengths         = models.TextField(blank=True, default="[]")
    weaknesses        = models.TextField(blank=True, default="[]")
    confidence_score  = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    eye_contact_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interview with {self.company_name} - {self.student.full_name}"


# ================= COMMUNICATION SKILLS =================

class CommunicationSession(models.Model):
    student          = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='comm_sessions')
    score            = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    overall_feedback = models.TextField(blank=True, default='')
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comm Session - {self.student.full_name} ({self.created_at.strftime('%Y-%m-%d')})"

class CommunicationTurn(models.Model):
    session           = models.ForeignKey(CommunicationSession, on_delete=models.CASCADE, related_name='turns')
    user_text         = models.TextField()
    ai_text           = models.TextField()
    coaching_feedback = models.TextField(blank=True, default='')
    score             = models.IntegerField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Turn in {self.session}"

# ================= INTELLIGENT RECOMMENDATION (HOLISTIC) =================

class IntelligentRecommendation(models.Model):
    student               = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name='intelligent_rec')
    strengths             = models.JSONField(default=list, blank=True)
    improvements          = models.JSONField(default=list, blank=True)
    weekly_plan           = models.JSONField(default=list, blank=True)
    daily_tasks           = models.JSONField(default=list, blank=True)
    learning_path         = models.JSONField(default=list, blank=True)
    readiness_score       = models.IntegerField(default=0)
    priority_areas        = models.JSONField(default=list, blank=True)
    motivational_feedback = models.TextField(blank=True)
    updated_at            = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Intelligent Rec for {self.student.full_name or self.student.user.username}"
