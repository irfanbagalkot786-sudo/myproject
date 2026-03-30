from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .forms import LoginForm, StudentProfileForm
from .models import StudentProfile, Skill, StudentSkill, Project, Resume, ResumeAnalysis, Company, JobRole, Recommendation, Question
from .models import LearningPath, Assessment

import os
import json
import google.generativeai as genai   # ← THIS must be at the top
import PyPDF2                          # ← THIS too

# ================= REGISTER VIEW =================

def register_view(request):

    if request.method == "POST":

        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Create Student Profile automatically
        StudentProfile.objects.create(
            user=user,
            full_name=username
        )

        messages.success(request, "Registration successful. Please login.")
        return redirect('login')

    return render(request, "register.html")


# ================= LOGIN VIEW =================

def login_view(request):

    form = LoginForm()

    if request.method == "POST":

        form = LoginForm(request.POST)

        if form.is_valid():

            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(
                request,
                username=username,
                password=password
            )

            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password")

        else:
            messages.error(request, "Invalid captcha")

    return render(request, "login.html", {'form': form})


# ================= LOGOUT VIEW =================

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ================= DASHBOARD VIEW =================

@login_required
def dashboard(request):
    # FIXED: Proper way to get student profile
    try:
        student_profile = StudentProfile.objects.get(user=request.user)
    except StudentProfile.DoesNotExist:
        student_profile = None
    
    # Get stats (optional)
    total_jobs = 100  # Replace with your job count
    applied_jobs = 5  # Replace with actual count
    
    context = {
        'student_profile': student_profile,
        'total_jobs': total_jobs,
        'applied_jobs': applied_jobs,
    }
    return render(request, 'dashboard.html', context)

# ================= STUDENT PROFILE VIEW ===============

@login_required
def student_profile(request):
    student, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': request.user.get_full_name() or request.user.username
        }
    )

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('student_profile')
        else:
            messages.error(request, 'Please fix the errors.')
    else:
        form = StudentProfileForm(instance=student)

    return render(request, 'student_profile.html', {
        'student': student,
        'form': form,
        'student_skills': StudentSkill.objects.filter(student=student),  # ✅ FIXED
    })
#=======SKILL VIEW =================

@login_required
def skills_view(request):

    student, created = StudentProfile.objects.get_or_create(user=request.user)
    skills = Skill.objects.all()
    student_skills = StudentSkill.objects.filter(student=student)

    if request.method == "POST":

        skill_id = request.POST.get('skill')
        level = request.POST.get('level')

        skill = Skill.objects.get(id=skill_id)

        # Avoid duplicate skills
        if StudentSkill.objects.filter(student=student, skill=skill).exists():
            messages.error(request, "Skill already added")
        else:
            StudentSkill.objects.create(
                student=student,
                skill=skill,
                level=level
            )
            messages.success(request, "Skill added successfully")

        return redirect('skills')

    context = {
        'skills': skills,
        'student_skills': student_skills
    }

    return render(request, "skills.html", context)

from .models import LearningPath, StudentSkill



#=================project view================

#ADD PROJECT
@login_required
def add_project(request):
    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        github_link = request.POST.get('github_link', '').strip()

        if title and description and github_link:
            Project.objects.create(
                user=request.user,          # student → user
                title=title,
                description=description,
                github_link=github_link,
            )
            messages.success(request, 'Project added successfully!')
            return redirect('projects')
        else:
            messages.error(request, 'Please fill in all fields.')

    return render(request, 'add_project.html')

#VIEW PROJECTS
@login_required
def view_projects(request):
    projects = Project.objects.filter(user=request.user).order_by('-id')  # student → user
    return render(request, 'view_projects.html', {'projects': projects})


#DELETE PROJECT
@login_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)  # student → user
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Project removed.')
    return redirect('projects')

# ================= LEARNING PATH VIEW =================

@login_required
def learning_path(request):

    student, created = StudentProfile.objects.get_or_create(user=request.user)

    # Get student skills
    student_skills = StudentSkill.objects.filter(student=student)

    # Auto-generate suggestions (simple AI logic)
    suggestions = []

    for s in student_skills:
        if s.skill.name.lower() == "python":
            suggestions.append("Learn Data Structures in Python")
            suggestions.append("Build Django Projects")

        if s.skill.name.lower() == "html":
            suggestions.append("Learn CSS and JavaScript")

        if s.skill.name.lower() == "java":
            suggestions.append("Practice OOPs and Spring Boot")

    # Save suggestions (avoid duplicates)
    for sug in suggestions:
        if not LearningPath.objects.filter(student=student, title=sug).exists():
            LearningPath.objects.create(
                student=student,
                title=sug,
                description="Recommended based on your skills"
            )

    paths = LearningPath.objects.filter(student=student)

    return render(request, "learning_path.html", {'paths': paths})

from .models import Question, Assessment
import json

# ================= TAKE TEST =================

@login_required
def test(request):
    questions = Question.objects.all()
    return render(request, 'test.html', {'questions': questions})

def result(request):
    # Block direct access — only allow after a POST submission
    if request.method != 'POST':
        return redirect('test')

    questions = Question.objects.all()
    score = 0

    for q in questions:
        submitted = request.POST.get(str(q.id))
        if submitted and submitted == q.correct_answer:  # adjust field name
            score += 1

    total = questions.count()
    return render(request, 'result.html', {'score': score, 'total': total})

# ── PDF TEXT EXTRACTION HELPER ──

def extract_text_from_pdf(file):
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
        print("PDF PAGES:", len(reader.pages))
        print("PDF TEXT SAMPLE:", text[:200])
        return text
    except Exception as e:
        print("PDF EXTRACT ERROR:", e)
        return ""

# ================= UPLOAD RESUME =================

@login_required
def upload_resume(request):
    if request.method == "POST":
        file = request.FILES.get('resume')
        print("=== UPLOAD RESUME CALLED ===")
        print("FILE:", file)

        if not file:
            print("NO FILE RECEIVED")
            messages.error(request, "Please select a file.")
            return redirect('upload_resume')

        print("FILE NAME:", file.name)

        # Save resume
        try:
            resume = Resume.objects.create(
                student=request.user.studentprofile,
                file=file
            )
            print("RESUME SAVED:", resume.id)
        except Exception as e:
            print("SAVE ERROR:", e)
            messages.error(request, f"Save error: {e}")
            return redirect('upload_resume')

        # Extract text
        
        try:
            file.seek(0)  # reset file pointer to beginning
            if file.name.lower().endswith('.pdf'):
                resume_text = extract_text_from_pdf(file)
            else:
                resume_text = file.read().decode('utf-8')

            print("TEXT EXTRACTED, length:", len(resume_text))

            if len(resume_text.strip()) == 0:
                resume_text = "No text could be extracted from this resume."

        except Exception as e:
            print("EXTRACT ERROR:", e)
            messages.error(request, f"Could not read file: {e}")
            return redirect('upload_resume')
        

        # Gemini AI
        try:
            print("CALLING GEMINI...")
            genai.configure(api_key="AIzaSyD6ClT2cU6zIS7Tu1thWyG3nrvF5a-15uA")
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            prompt = f"""
Analyze this resume and return ONLY valid JSON, no extra text, no backticks.

Resume:
{resume_text[:3000]}

Return exactly:
{{
    "score": <number 0-100>,
    "feedback": "<feedback text>",
    "recommended_roles": ["role1", "role2", "role3"]
}}
"""
            response = model.generate_content(prompt)
            raw = response.text.strip()
            print("GEMINI RESPONSE:", raw[:200])

            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)
            print("PARSED DATA:", data)

        except json.JSONDecodeError as e:
            print("JSON ERROR:", e)
            messages.error(request, f"AI response error: {e}")
            return redirect('upload_resume')
        except Exception as e:
            print("GEMINI ERROR:", e)
            messages.error(request, f"Gemini error: {e}")
            return redirect('upload_resume')

        # Save analysis
        try:
            analysis, created = ResumeAnalysis.objects.get_or_create(resume=resume)
            analysis.analysis_score = data.get('score', 0)
            analysis.feedback = data.get('feedback', 'No feedback.')
            analysis.save()
            print("ANALYSIS SAVED")
        except Exception as e:
            print("ANALYSIS SAVE ERROR:", e)
            messages.error(request, f"Analysis save error: {e}")
            return redirect('upload_resume')

        request.session['recommended_roles'] = data.get('recommended_roles', [])

        print("REDIRECTING TO analyze_resume...")
        messages.success(request, "Resume analyzed successfully!")
        return redirect('analyze_resume')

    print("GET REQUEST - showing upload page")
    return render(request, "upload_resume.html")

        


# ================= ANALYZE RESUME =================

@login_required
def analyze_resume(request):
    student, created = StudentProfile.objects.get_or_create(user=request.user)
    resume = Resume.objects.filter(student=student).last()

    if not resume:
        return redirect('upload_resume')

    analysis, created = ResumeAnalysis.objects.get_or_create(resume=resume)

    # Get recommended roles from session
    recommended_roles = request.session.pop('recommended_roles', [])

    return render(request, "resume_result.html", {
        'analysis': analysis,
        'recommended_roles': recommended_roles,
    })
 #================== COMPANY LIST VIEW =================

@login_required
def company_list(request):

        companies = Company.objects.all()

        return render(request, "company_list.html", {
        'companies': companies
        })

#=================== JOB LIST VIEW =================
@login_required
def job_list(request):

    jobs = JobRole.objects.all()

    return render(request, "job_list.html", {
        'jobs': jobs
    })

#=======================AI RECOMMENDATION  =================

@login_required
def generate_recommendations(request):

    student, created = StudentProfile.objects.get_or_create(user=request.user)

    # Get student skills
    student_skills = StudentSkill.objects.filter(student=student)
    student_skill_list = [s.skill for s in student_skills]

    # Get all jobs
    jobs = JobRole.objects.all()

    # Clear old recommendations
    Recommendation.objects.filter(student=student).delete()

    for job in jobs:

        job_skills = job.required_skills.all()

        matched = []
        missing = []

        for skill in job_skills:
            if skill in student_skill_list:
                matched.append(skill)
            else:
                missing.append(skill)

        # Calculate match %
        if job_skills.count() > 0:
            match_percentage = (len(matched) / job_skills.count()) * 100
        else:
            match_percentage = 0

        # Save recommendation
        rec = Recommendation.objects.create(
            student=student,
            job_role=job,
            match_percentage=match_percentage,
            recommendation_reason="Skill match analysis"
        )

        rec.matching_skills.set(matched)
        rec.missing_skills.set(missing)

    return redirect('recommendations')


@login_required
def recommendations_view(request):

    student = request.user.studentprofile

    recs = Recommendation.objects.filter(student=student).order_by('-match_percentage')

    return render(request, "recommendations.html", {
        'recommendations': recs
    })