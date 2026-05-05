from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.core.management import call_command
from .forms import LoginForm, StudentProfileForm
from .models import (
    StudentProfile, Skill, StudentSkill, CustomSkill, Project, Resume,
    ResumeAnalysis, Company, JobRole, Recommendation, Question, InterviewSession,
    CommunicationSession, CommunicationTurn, IntelligentRecommendation, Assessment
)
import random
import json
import os
import subprocess
import time
import requests
import fitz  
import base64
import PyPDF2
import whisper
import re
from pathlib import Path
from openai import OpenAI
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile

# ─── Config ─────────────────────────────────────────────────────────────────
def load_openai_key():
    """Loads the OpenAI API Key from env.html in the project root."""
    try:
        base_dir = Path(__file__).resolve().parent.parent
        env_file = base_dir / "env.html"
        if env_file.exists():
            content = env_file.read_text(encoding='utf-8')
            match = re.search(r'OPENAI_API_KEY\s*=\s*"([^"]+)"', content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error loading OpenAI key: {e}")
    return os.getenv("OPENAI_API_KEY", "")

OPENAI_API_KEY = load_openai_key()
client = OpenAI(api_key=OPENAI_API_KEY)
# ────────────────────────────────────────────────────────────────────────────

model = None

def get_model():
    global model
    if model is None:
        model = whisper.load_model("small")
    return model

def your_view(request):
    model = get_model()

def openai_generate(prompt, image_parts=None, mime_type="image/png"):
    """
    Standard AI generation using OpenAI's GPT-4o-mini.
    Supports text-only and vision (image) inputs.
    """
    try:
        messages = []
        if image_parts:
            content = [{"type": "text", "text": prompt}]
            for img_base64 in image_parts:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{img_base64}"}
                })
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={ "type": "json_object" } if "JSON" in prompt.upper() else None
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return None

# ================= REGISTER VIEW =================

def register_view(request):
    if request.method == "POST":
        username         = request.POST.get('username')
        email            = request.POST.get('email')
        password         = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password)
        StudentProfile.objects.create(user=user, full_name=username)
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
            user     = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password")
        else:
            messages.error(request, "Form is invalid")
    return render(request, "login.html", {'form': form})


# ================= LOGOUT VIEW =================

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ================= DASHBOARD VIEW =================

@login_required
def dashboard(request):
    student = request.user.studentprofile
    # Custom (student-defined) skills
    custom_skills = CustomSkill.objects.filter(student=student)
    return render(request, 'dashboard.html', {
        'student':       student,
        'custom_skills': custom_skills,
    })


# ================= STUDENT PROFILE VIEW =================

@login_required
def student_profile(request):
    student, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': request.user.username}
    )

    if request.method == 'POST':
        student.full_name = request.POST.get('full_name', '').strip()
        student.college   = request.POST.get('college',   '').strip()
        student.branch    = request.POST.get('branch',    '').strip()

        cgpa_raw = request.POST.get('cgpa', '').strip()
        try:
            val = float(cgpa_raw)
            student.cgpa = max(0, min(10, val))
        except (ValueError, TypeError):
            student.cgpa = 0

        grad_raw = request.POST.get('graduation_year', '').strip()
        try:
            student.graduation_year = int(grad_raw) if grad_raw else None
        except ValueError:
            student.graduation_year = None

        student.phone        = request.POST.get('phone', '').strip()
        student.job_role     = request.POST.get('job_role', '').strip()
        student.languages    = ','.join(request.POST.getlist('languages'))
        work_mode_val        = request.POST.get('work_mode', '').strip()
        student.work_mode    = work_mode_val if work_mode_val else None
        student.linkedin_url = request.POST.get('linkedin_url', '').strip()
        student.github_url   = request.POST.get('github_url',   '').strip()

        remove_photo = request.POST.get('remove_photo', '0')
        if remove_photo == '1':
            if student.profile_photo:
                student.profile_photo.delete(save=False)
            student.profile_photo = None
        elif request.FILES.get('profile_photo'):
            student.profile_photo = request.FILES['profile_photo']

        student.save()

        # Return JSON if request is AJAX (from dashboard modal)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
            return JsonResponse({'status': 'ok', 'message': 'Profile updated successfully!'})

        messages.success(request, 'Profile updated successfully!')
        return redirect('student_profile')

    custom_skills = CustomSkill.objects.filter(student=student)
    context = {
        'student':           student,
        'custom_skills':     custom_skills,
        'student_languages': student.get_languages_list(),
    }
    return render(request, 'student_profile.html', context)


# ================= REMOVE PHOTO =================

def remove_photo(request):
    if request.method == "POST":
        student = request.user.studentprofile
        student.profile_photo.delete(save=True)
    return redirect('student_profile')


# ================= UPDATE PHOTO =================

def update_photo(request):
    if request.method == "POST":
        student = request.user.studentprofile
        if 'profile_photo' in request.FILES:
            student.profile_photo = request.FILES['profile_photo']
            student.save()
    return redirect('dashboard')


# ================= CUSTOM SKILL: ADD =================

@login_required
def add_custom_skill(request):
    """Add a student-defined skill with a 1-5 level. Always returns JSON."""
    if request.method == "POST":
        student    = request.user.studentprofile
        skill_name = request.POST.get('skill_name', '').strip()
        try:
            level = int(request.POST.get('level', 1))
            level = max(1, min(5, level))
        except (ValueError, TypeError):
            level = 1

        if skill_name:
            CustomSkill.objects.update_or_create(
                student=student,
                skill_name__iexact=skill_name,
                defaults={'skill_name': skill_name, 'level': level}
            )
            return JsonResponse({'status': 'ok', 'message': f'"{skill_name}" saved!'})
        return JsonResponse({'status': 'error', 'message': 'Please enter a skill name.'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid method.'}, status=405)


# ================= CUSTOM SKILL: DELETE =================

@login_required
def delete_custom_skill(request, skill_id):
    student = request.user.studentprofile
    skill   = get_object_or_404(CustomSkill, id=skill_id, student=student)
    if request.method == "POST":
        skill.delete()
    referer = request.META.get('HTTP_REFERER', '')
    if 'dashboard' in referer:
        return redirect('dashboard')
    return redirect('skills')


# ================= LEGACY delete_skill (kept for old URL compatibility) =================

def delete_skill(request, skill_id):
    """Kept for backward compatibility — now delegates to delete_custom_skill."""
    return delete_custom_skill(request, skill_id)


# ================= SKILLS PAGE VIEW =================

@login_required
def skills_view(request):
    student, _ = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': request.user.username}
    )

    if request.method == 'POST':
        skill_name = request.POST.get('skill_name', '').strip()
        try:
            level = int(request.POST.get('level', 1))
            level = max(1, min(5, level))
        except (ValueError, TypeError):
            level = 1

        if skill_name:
            CustomSkill.objects.update_or_create(
                student=student,
                skill_name__iexact=skill_name,
                defaults={'skill_name': skill_name, 'level': level}
            )
            messages.success(request, f'"{skill_name}" added!')
        else:
            messages.error(request, 'Please enter a skill name.')
        return redirect('skills')

    custom_skills = CustomSkill.objects.filter(student=student)
    return render(request, 'skills.html', {'custom_skills': custom_skills})


# ================= PROJECT VIEWS =================

@login_required
def add_project(request):
    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        github_link = request.POST.get('github_link', '').strip()

        if title and description and github_link:
            Project.objects.create(
                user=request.user, title=title,
                description=description, github_link=github_link,
            )
            messages.success(request, 'Project added successfully!')
            return redirect('projects')
        else:
            messages.error(request, 'Please fill in all fields.')

    return render(request, 'add_project.html')


@login_required
def view_projects(request):
    projects = Project.objects.filter(user=request.user).order_by('-id')
    return render(request, 'view_projects.html', {'projects': projects})


@login_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Project removed.')
    return redirect('projects')


# ================= TEST & RESULT =================

@login_required
def test(request):
    topic_slug     = request.GET.get('topic', '')
    questions_list = []

    if topic_slug:
        questions = Question.objects.filter(category=topic_slug).order_by('?')[:10]
        for q in questions:
            questions_list.append({
                'q':       q.question_text,
                'options': [q.option1, q.option2, q.option3, q.option4],
                'answer':  [q.option1, q.option2, q.option3, q.option4].index(q.correct_answer)
            })

    from .models import Company
    companies = Company.objects.all()
    return render(request, 'test.html', {
        'questions_json': json.dumps(questions_list),
        'companies':      companies
    })


@csrf_exempt
@login_required
def save_assessment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            from .models import Assessment
            Assessment.objects.create(
                student=request.user.studentprofile,
                score=data.get('score', 0),
                total_questions=data.get('total', 0)
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def result(request):
    return render(request, 'result.html')


# ================= PDF → BASE64 IMAGES =================

def pdf_to_base64_images(file):
    file.seek(0)
    pdf_bytes = file.read()
    doc       = fitz.open(stream=pdf_bytes, filetype="pdf")
    images    = []
    for page in doc:
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
        images.append(b64)
    return images


# ================= UPLOAD RESUME =================

@login_required
def upload_resume(request):
    if request.method == "POST":
        file = request.FILES.get('resume')
        if not file:
            messages.error(request, "Please select a file.")
            return redirect('upload_resume')

        try:
            resume = Resume.objects.create(student=request.user.studentprofile, file=file)
        except Exception as e:
            messages.error(request, f"Save error: {e}")
            return redirect('upload_resume')

        fname_lower = file.name.lower()
        use_vision  = fname_lower.endswith('.pdf') or fname_lower.endswith(('.png', '.jpg', '.jpeg'))

        if use_vision:
            if fname_lower.endswith('.pdf'):
                page_images = pdf_to_base64_images(file)
                mime_type   = "image/png"
            else:
                file.seek(0)
                img_data    = base64.b64encode(file.read()).decode('utf-8')
                page_images = [img_data]
                mime_type   = "image/jpeg" if fname_lower.endswith(('.jpg', '.jpeg')) else "image/png"
        else:
            file.seek(0)
            resume_text = file.read().decode('utf-8', errors='ignore')

        json_instruction = """
Analyze this resume and return JSON:
{
  "score": <0-100>,
  "ats_score": <0-100>,
  "summary": "...",
  "strong_points": [{"title": "...", "detail": "..."}],
  "weak_points": [{"title": "...", "detail": "..."}],
  "skills_present": [],
  "skills_missing": [],
  "ats_keywords": [],
  "pro_tips": [],
  "recommended_roles": []
}
"""

        try:
            if use_vision:
                raw = openai_generate(json_instruction, image_parts=page_images, mime_type=mime_type)
            else:
                raw = openai_generate(f"{json_instruction}\n\nResume: {resume_text[:5000]}")

            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)
            print("PARSED DATA — score:", data.get('score'), "| ats:", data.get('ats_score'))

        except json.JSONDecodeError as e:
            print("JSON ERROR:", e)
            messages.error(request, f"AI response parse error: {e}")
            return redirect('upload_resume')
        except Exception as e:
            print("GEMINI ERROR:", e)
            messages.error(request, f"Gemini error: {e}")
            return redirect('upload_resume')

        try:
            analysis, _             = ResumeAnalysis.objects.get_or_create(resume=resume)
            analysis.analysis_score = data.get('score', 0)
            analysis.ats_score      = data.get('ats_score', 0)
            analysis.feedback       = data.get('feedback') or data.get('summary', 'No feedback.')
            analysis.summary        = data.get('summary', '')
            analysis.strong_points  = data.get('strong_points', [])
            analysis.weak_points    = data.get('weak_points', [])
            analysis.skills_present = data.get('skills_present', [])
            analysis.skills_missing = data.get('skills_missing', [])
            analysis.ats_keywords   = data.get('ats_keywords', [])
            analysis.pro_tips       = data.get('pro_tips', [])
            analysis.save()
            print("ANALYSIS SAVED — score:", analysis.analysis_score)
        except Exception as e:
            print("ANALYSIS SAVE ERROR:", e)
            messages.error(request, f"Analysis save error: {e}")
            return redirect('upload_resume')

        request.session['recommended_roles'] = data.get('recommended_roles', [])
        messages.success(request, "Resume analyzed successfully!")
        return redirect('analyze_resume')

    print("GET REQUEST - showing upload page")
    return render(request, "upload_resume.html")


# ================= ANALYZE RESUME =================

@login_required
def analyze_resume(request):
    student    = request.user.studentprofile
    resume_obj = Resume.objects.filter(student=student).last()

    if not resume_obj:
        messages.error(request, "No resume found. Please upload one first.")
        return redirect('upload_resume')

    existing_analysis = ResumeAnalysis.objects.filter(resume=resume_obj).last()

    if existing_analysis and existing_analysis.analysis_score > 0:
        recommended_roles = request.session.get('recommended_roles', [])
        return render(request, "upload_resume.html", {
            'analysis':          existing_analysis,
            'recommended_roles': recommended_roles,
            'student':           student,
        })

    resume_text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(resume_obj.file.path)
        for page in pdf_reader.pages:
            resume_text += page.extract_text() or ""
    except Exception as e:
        print(f"PDF Reader Error: {e}")
        resume_text = "Could not parse PDF content."

    try:
        prompt = f"""
You are a senior technical recruiter. Analyze this resume and return ONLY valid JSON.
Return this exact JSON (no backticks, no markdown):
{{
  "score": <integer 0-100>,
  "ats_score": <integer 0-100>,
  "summary": "<2-3 sentence honest verdict>",
  "strong_points": [{{"title": "<strength>", "detail": "<evidence>"}}],
  "weak_points": [{{"title": "<weakness>", "detail": "<fix>"}}],
  "skills": ["skill1", "skill2"],
  "skills_present": ["skill1", "skill2"],
  "skills_missing": ["skill1", "skill2"],
  "ats_keywords": ["keyword1", "keyword2"],
  "pro_tips": ["<tip1>", "<tip2>"],
  "experience_years": <number>,
  "recommended_roles": ["Role 1", "Role 2", "Role 3", "Role 4", "Role 5"],
  "feedback": "<same as summary>"
}}

Resume:
{resume_text[:5000]}
"""
        raw_text = openai_generate(prompt)
        if not raw_text:
            raise Exception("No response from OpenAI")
        raw_text = raw_text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        data = json.loads(raw_text)

        analysis, _ = ResumeAnalysis.objects.update_or_create(
            resume=resume_obj,
            defaults={
                'experience_years': data.get('experience_years', 0),
                'analysis_score':   data.get('score', 0),
                'ats_score':        data.get('ats_score', 0),
                'feedback':         data.get('feedback') or data.get('summary', ''),
                'summary':          data.get('summary', ''),
                'strong_points':    data.get('strong_points', []),
                'weak_points':      data.get('weak_points', []),
                'skills_present':   data.get('skills_present', []),
                'skills_missing':   data.get('skills_missing', []),
                'ats_keywords':     data.get('ats_keywords', []),
                'pro_tips':         data.get('pro_tips', []),
            }
        )

        for s_name in data.get('skills', []):
            skill_obj, _ = Skill.objects.get_or_create(name=s_name.strip().title())
            analysis.extracted_skills.add(skill_obj)
            StudentSkill.objects.get_or_create(student=student, skill=skill_obj)

        recommended_roles = data.get('recommended_roles', [])
        request.session['recommended_roles'] = recommended_roles

    except Exception as e:
        print(f"AI Error in analyze_resume: {e}")
        analysis, _ = ResumeAnalysis.objects.update_or_create(
            resume=resume_obj,
            defaults={
                'analysis_score': 0,
                'feedback': "Could not analyze resume. Please ensure the file is readable."
            }
        )
        recommended_roles = []

    return render(request, "upload_resume.html", {
        'analysis':          analysis,
        'recommended_roles': request.session.get('recommended_roles', recommended_roles),
        'student':           student,
    })


# ================= COMPANY =================

@login_required
def company_list(request):
    companies      = Company.objects.all()
    companies_meta = {}

    for company in companies:
        job  = company.jobrole_set.first()
        tips = list(company.tips.values_list('tip_text', flat=True))

        companies_meta[str(company.id)] = {
            'banner':     company.name.split()[0],
            'bannerBg':   company.banner_gradient or 'linear-gradient(135deg,#0aa3b5 0%,#088a9a 100%)',
            'logo':       company.logo_text or company.name[:2].upper(),
            'logoBg':     company.banner_gradient or 'var(--gradient)',
            'accent':     '#0aa3b5',
            'name':       company.name,
            'sub':        f"{company.industry} · {company.employee_count} Employees",
            'about':      company.about_text or company.description,
            'facts': [
                {'icon': 'fa-users',      'label': 'Employees', 'val': company.employee_count},
                {'icon': 'fa-globe',      'label': 'Countries', 'val': company.countries_count},
                {'icon': 'fa-chart-line', 'label': 'Revenue',   'val': company.revenue},
                {'icon': 'fa-star',       'label': 'Glassdoor', 'val': f"{company.glassdoor_rating} / 5"},
            ],
            'roles': [
                {'title': j.title, 'pkg': j.salary_range, 'label': j.experience_level.title()}
                for j in company.jobrole_set.all()
            ],
            'requirements': json.loads(job.eligibility_json)     if job and job.eligibility_json     else [],
            'steps':        json.loads(job.interview_steps_json) if job and job.interview_steps_json else [],
            'tips':         tips,
            'website':      company.website
        }

    return render(request, 'companies.html', {
        'companies':           companies,
        'companies_meta_json': json.dumps(companies_meta)
    })


# ================= JOB LIST =================

@login_required
def job_list(request):
    return render(request, "job_list.html", {'jobs': []})


# ================= AI RECOMMENDATIONS =================

@login_required
def recommendations(request):
    student = request.user.studentprofile
    recs    = Recommendation.objects.filter(student=student).order_by('-match_percentage')
    intelligent_rec = IntelligentRecommendation.objects.filter(student=student).first()
    
    return render(request, "recommendations.html", {
        'recommendations': recs,
        'intelligent_rec': intelligent_rec,
        'student': student
    })


@login_required
def generate_recommendations(request):
    student = request.user.studentprofile
    
    # 1. Traditional Job Matching (Existing Logic)
    student_skills = set(StudentSkill.objects.filter(student=student).values_list('skill__id', flat=True))
    roles          = JobRole.objects.all()

    Recommendation.objects.filter(student=student).delete()

    for role in roles:
        required_skills = set(role.required_skills.values_list('id', flat=True))
        if not required_skills:
            continue

        matching    = student_skills.intersection(required_skills)
        missing     = required_skills.difference(student_skills)
        skill_score = (len(matching) / len(required_skills)) * 70

        if role.min_cgpa > 0:
            cgpa_score = 30 if student.cgpa >= role.min_cgpa else (student.cgpa / role.min_cgpa) * 30
        else:
            cgpa_score = 30

        total_match = min(skill_score + cgpa_score, 100)
        rec = Recommendation.objects.create(student=student, job_role=role, match_percentage=total_match)
        rec.matching_skills.set(Skill.objects.filter(id__in=matching))
        rec.missing_skills.set(Skill.objects.filter(id__in=missing))

    # 2. Intelligent Holistic Analysis (New Logic)
    try:
        # Gather Student Data
        resume_analysis = ResumeAnalysis.objects.filter(resume__student=student).last()
        assessments = Assessment.objects.filter(student=student)
        interviews = InterviewSession.objects.filter(student=student)
        comm_sessions = CommunicationSession.objects.filter(student=student)
        custom_skills = CustomSkill.objects.filter(student=student)
        projects = Project.objects.filter(user=request.user)

        # Prepare metrics
        avg_apt_score = 0
        if assessments.exists():
            avg_apt_score = sum([a.score for a in assessments]) / assessments.count()
            
        avg_comm_score = 0
        if comm_sessions.exists():
            avg_comm_score = sum([s.score for s in comm_sessions]) / comm_sessions.count()

        avg_int_score = 0
        if interviews.exists():
            avg_int_score = sum([i.ai_score for i in interviews]) / interviews.count()

        prompt = f"""
        You are an Intelligent Career Coach. Analyze this student profile and generate a placement readiness plan.
        
        PROFILE DATA:
        - Name: {student.full_name}
        - Branch: {student.branch}, CGPA: {student.cgpa}
        - Resume Analysis: Score {resume_analysis.analysis_score if resume_analysis else 'N/A'}, Missing Skills: {resume_analysis.skills_missing if resume_analysis else 'N/A'}
        - Aptitude Test Avg: {avg_apt_score}%
        - Communication Avg: {avg_comm_score}%
        - Mock Interview Avg: {avg_int_score}%
        - Skills: {[s.skill_name for s in custom_skills]}
        - Projects: {[p.title for p in projects]}
        
        OUTPUT JSON FORMAT:
        {{
          "strengths": ["...", "..."],
          "improvements": ["...", "..."],
          "weekly_plan": ["Week 1: Focus on...", "Week 2: Focus on..."],
          "daily_tasks": ["...", "..."],
          "learning_path": ["...", "..."],
          "readiness_score": 0-100,
          "priority_areas": ["...", "..."],
          "motivational_feedback": "..."
        }}
        """
        
        raw = openai_generate(prompt)
        if raw:
            raw = raw.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
            data = json.loads(raw.strip())
            
            IntelligentRecommendation.objects.update_or_create(
                student=student,
                defaults={
                    'strengths': data.get('strengths', []),
                    'improvements': data.get('improvements', []),
                    'weekly_plan': data.get('weekly_plan', []),
                    'daily_tasks': data.get('daily_tasks', []),
                    'learning_path': data.get('learning_path', []),
                    'readiness_score': data.get('readiness_score', 0),
                    'priority_areas': data.get('priority_areas', []),
                    'motivational_feedback': data.get('motivational_feedback', '')
                }
            )

    except Exception as e:
        print(f"Error generating intelligent recommendations: {e}")
        messages.error(request, f"Intelligent Analysis Error: {str(e)}")

    messages.success(request, "Intelligent recommendations updated!")
    return JsonResponse({'status': 'success', 'message': 'Intelligent recommendations updated!'})


def company_details(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    return render(request, "company_details.html", {'company': company})


# ================= VIRTUAL INTERVIEW =================

@login_required
def virtual_interview(request):
    company_name   = request.GET.get('company', 'General')
    interview_type = request.GET.get('type', 'hr')
    return render(request, 'virtual_interview.html', {'company_name': company_name, 'interview_type': interview_type})


@csrf_exempt
@login_required
def generate_tech_questions(request):
    if request.method == 'POST':
        try:
            data     = json.loads(request.body)
            language = data.get('language', 'Python')
            prompt   = f"Generate exactly 9 technical interview questions for a candidate specializing in {language}. Return ONLY valid JSON as a list of strings: [\"question 1\", \"question 2\", ...]"
            raw = openai_generate(prompt)
            if not raw:
                raise Exception("No response from AI")
            raw = raw.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            questions = json.loads(raw.strip())
            return JsonResponse({'status': 'success', 'questions': questions[:9]})
        except Exception as e:
            print("ERROR generating tech questions:", e)
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


# ================= INTERVIEW ANALYSIS =================

def perform_full_interview_analysis(interview):
    print(f"🎬 Starting automatic analysis for Interview ID: {interview.id}")

    audio_path = extract_audio_from_video(interview.video_file)
    if not audio_path:
        print("❌ Audio extraction failed during automatic processing")
        return False

    print("🎤 Transcribing...")
    whisper_model = get_model()
    result        = whisper_model.transcribe(audio_path)
    transcript    = result.get("text", "")
    interview.transcript = transcript
    print(f"📝 Transcript length: {len(transcript)}")

    print("🧠 Analyzing with OpenAI...")
    analysis = analyze_transcript(transcript)

    content_score     = analysis.get("score", 70)
    confidence_score  = interview.confidence_score
    eye_contact_score = interview.eye_contact_score
    final_score       = int((content_score * 0.6) + (confidence_score * 0.2) + (eye_contact_score * 0.2))

    interview.ai_score    = max(0, min(100, final_score))
    interview.ai_feedback = f"{analysis.get('feedback', '')} \n\nBehavioral Analysis: {analysis.get('behavioral_feedback', 'Processed automatically.')}"

    strengths  = analysis.get("strengths")  or ["Good communication", "Willing to answer", "Basic understanding"]
    weaknesses = analysis.get("weaknesses") or ["Needs more clarity", "Lack of examples", "Short answers"]

    interview.strengths  = json.dumps(strengths)
    interview.weaknesses = json.dumps(weaknesses)
    interview.save()

    print(f"✅ Automatic analysis complete for Interview ID: {interview.id}")
    return True


@csrf_exempt
@login_required
def save_interview(request):
    if request.method == 'POST':
        video_blob   = request.FILES.get('video')
        company_name = request.POST.get('company_name', 'General')

        try:
            confidence_score = int(float(request.POST.get('confidence_score', 0)))
        except (ValueError, TypeError):
            confidence_score = 0

        try:
            eye_contact_score = int(float(request.POST.get('eye_contact_score', 0)))
        except (ValueError, TypeError):
            eye_contact_score = 0

        if video_blob:
            student   = request.user.studentprofile
            interview = InterviewSession.objects.create(
                student=student,
                company_name=company_name,
                video_file=video_blob,
                confidence_score=confidence_score,
                eye_contact_score=eye_contact_score
            )

            try:
                prompt = f"""
Analyze this interview for {company_name}.
Candidate behavioral metrics:
- Confidence Score: {confidence_score}%
- Eye Contact Score: {eye_contact_score}%

Return ONLY valid JSON:
{{
  "content_score": 0-100,
  "behavioral_feedback": "about confidence and eye contact",
  "general_feedback": "overall performance",
  "transcript": "summary",
  "strengths": ["point1", "point2", "point3"],
  "weaknesses": ["point1", "point2", "point3"]
}}
"""
                raw = openai_generate(prompt)
                if not raw:
                    raise Exception("No response from AI")
                raw = raw.strip()
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                data = json.loads(raw.strip())

                content_score = data.get('content_score', 70)
                final_score   = int((content_score * 0.6) + (confidence_score * 0.2) + (eye_contact_score * 0.2))

                interview.ai_score    = max(0, min(100, final_score))
                interview.ai_feedback = f"{data.get('general_feedback', '')} \n\nBehavioral Analysis: {data.get('behavioral_feedback', '')}"
                interview.transcript  = data.get('transcript', 'Transcript summary generated.')
                interview.save()

            except Exception as e:
                print("AI ANALYSIS ERROR:", e)
                final_score           = int((75 * 0.6) + (confidence_score * 0.2) + (eye_contact_score * 0.2))
                interview.ai_score    = final_score
                interview.ai_feedback = "AI analysis encountered an error, but your behavioral scores were factored in."
                interview.transcript  = "[Automated Summary due to analysis error]"
                interview.save()

            perform_full_interview_analysis(interview)
            return JsonResponse({'status': 'success', 'message': 'Interview saved and processed!', 'id': interview.id})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def extract_audio_from_video(video_field):
    try:
        video_path    = video_field.path
        base_name     = os.path.splitext(os.path.basename(video_path))[0]
        audio_folder  = os.path.join(settings.MEDIA_ROOT, "audio")
        os.makedirs(audio_folder, exist_ok=True)
        audio_path    = os.path.join(audio_folder, base_name + ".wav")
        command = ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path]
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("✅ Audio extracted:", audio_path)
        return audio_path
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg error:", e.stderr.decode())
        return None
    except Exception as e:
        print("❌ General error:", str(e))
        return None


def process_interview(request, interview_id):
    interview = InterviewSession.objects.get(id=interview_id)
    perform_full_interview_analysis(interview)
    return redirect('interview_detail', interview_id=interview.id)


def analyze_transcript(transcript):
    prompt = f"""
You are an expert HR interviewer.
Analyze the following interview transcript.
Transcript:
{transcript}

INSTRUCTIONS:
- Always return at least 3 strengths
- Always return at least 3 weaknesses
- Be specific and meaningful

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "score": number between 0-100,
  "strengths": ["point1", "point2", "point3"],
  "weaknesses": ["point1", "point2", "point3"],
  "feedback": "detailed feedback"
}}
"""
    raw = openai_generate(prompt)
    if not raw:
        return {"score": 70, "strengths": [], "weaknesses": [], "feedback": "Analysis failed."}
    raw = raw.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    print("🔥 RAW AI RESPONSE:", raw)
    data = json.loads(raw.strip())
    return data


@login_required
def interview_results(request):
    try:
        call_command('migrate', interactive=False)
    except Exception as e:
        print(f"Migration error: {e}")
    student    = request.user.studentprofile
    interviews = InterviewSession.objects.filter(student=student).order_by('-created_at')
    return render(request, 'interview_results.html', {'interviews': interviews})


@login_required
def interview_detail(request, interview_id):
    interview = get_object_or_404(
        InterviewSession, id=interview_id, student=request.user.studentprofile
    )
    try:
        strengths = json.loads(interview.strengths) if interview.strengths else []
    except (json.JSONDecodeError, TypeError):
        strengths = []
    try:
        weaknesses = json.loads(interview.weaknesses) if interview.weaknesses else []
    except (json.JSONDecodeError, TypeError):
        weaknesses = []

    return render(request, 'interview_detail.html', {
        'interview': interview,
        'strengths': strengths,
        'weaknesses': weaknesses,
    })


@login_required
def delete_interview(request, interview_id):
    if request.method == "POST":
        try:
            student   = request.user.studentprofile
            interview = InterviewSession.objects.get(id=interview_id, student=student)
            if interview.video_file:
                interview.video_file.delete()
            interview.delete()
            return JsonResponse({'status': 'success', 'message': 'Interview deleted successfully.'})
        except InterviewSession.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Interview not found.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


# ================= AI QUESTION GENERATION =================

@csrf_exempt
def generate_ai_questions(request):
    if request.method == 'POST':
        try:
            body        = json.loads(request.body)
            topic_label = body.get('topic', 'General')

            prompt = f"""You are an expert exam question creator for placement aptitude tests in India.
Generate exactly 50 unique multiple-choice questions for the topic: "{topic_label}".
STRICT RULES:
- Each question must have exactly 4 options
- Only one option is correct
- Return ONLY valid JSON, no markdown, no backticks

Exact JSON structure:
{{"questions": [{{"question": "Question text?", "options": ["Option A", "Option B", "Option C", "Option D"], "correct": 0, "explanation": "One sentence explanation."}}]}}
Generate all 50 questions now."""

            print(f"Calling AI for topic: {topic_label}")
            raw = openai_generate(prompt)
            if not raw:
                raise Exception("No response from AI")
            raw = raw.strip()
            print(f"AI raw response length: {len(raw)}")

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            import re
            raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)
            raw = re.sub(r'(?<!\\)\n', ' ', raw)
            raw = re.sub(r'(?<!\\)\r', '', raw)
            raw = re.sub(r'(?<!\\)\t', ' ', raw)
            raw = raw.strip()

            parsed    = json.loads(raw)
            questions = parsed.get('questions', [])
            print(f"Parsed {len(questions)} questions successfully")
            return JsonResponse({'status': 'success', 'questions': questions})

        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            try:
                import re
                raw = re.sub(r'[\x00-\x1f\x7f]', ' ', raw)
                raw = re.sub(r',\s*}', '}', raw)
                raw = re.sub(r',\s*]', ']', raw)
                parsed    = json.loads(raw)
                questions = parsed.get('questions', [])
                return JsonResponse({'status': 'success', 'questions': questions})
            except Exception as e2:
                print(f"Fallback also failed: {e2}")
                return JsonResponse({'status': 'error', 'message': f'JSON parse error: {str(e)}'}, status=500)
        except Exception as e:
            print(f"generate_ai_questions ERROR: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)


# ================= COMMUNICATION SKILLS AGENT =================

@login_required
def communication_skills(request):
    """Renders the main communication practice interface."""
    return render(request, 'communication_skills.html')

# ── REPLACE YOUR EXISTING process_comm_turn VIEW IN views.py WITH THIS ──
# Task 3: Enriched AI prompt with detailed grammar rules, vocabulary categories,
# fluency metrics, and professional communication coaching content.

# ── REPLACE YOUR EXISTING process_comm_turn VIEW IN views.py WITH THIS ──

@csrf_exempt
@login_required
def process_comm_turn(request):
    """AJAX endpoint — conversational AI tutor that teaches, explains, and coaches communication."""
    if request.method == 'POST':
        try:
            data       = json.loads(request.body)
            user_text  = data.get('text', '').strip()
            session_id = data.get('session_id')
            history    = data.get('history', [])   # full conversation history from frontend

            if not user_text:
                return JsonResponse({'status': 'error', 'message': 'No text provided'})

            student = request.user.studentprofile

            # Get or create session
            if session_id:
                try:
                    session = CommunicationSession.objects.get(id=session_id, student=student)
                except CommunicationSession.DoesNotExist:
                    session = CommunicationSession.objects.create(student=student)
            else:
                session = CommunicationSession.objects.create(student=student)

            # ── SYSTEM PROMPT: Conversational tutor + teacher ──
            system_prompt = """You are "SmartPlace Communication Coach" — a warm, friendly, highly intelligent English communication tutor AND conversational partner for students preparing for corporate placements in India.

You have TWO modes that you naturally blend together:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODE 1: NATURAL CONVERSATION PARTNER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You hold real back-and-forth conversations just like a human would:
- If someone says "How are you?" → Reply naturally: "I'm doing great, thank you for asking! How are you feeling today? Ready for some practice?"
- If someone says "I am fine" → Continue naturally: "Wonderful! I'm glad to hear that. So, shall we dive into some communication practice today? What topic would you like to work on?"
- If someone introduces themselves → Respond warmly and ask a follow-up question about their goals
- If someone asks "What is your name?" → "I am SmartPlace Communication Coach, your personal guide to mastering professional English! What shall I call you?"
- Always respond to what was SAID first, then coach gently
- Keep the conversation flowing: question → answer → question → answer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODE 2: ENGLISH TEACHER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When the student asks about grammar, vocabulary, tenses — TEACH them fully with examples:

TENSES (when asked, teach rule + examples + drill):
Simple Present: "I work every day." — habitual actions, general truths
Present Continuous: "I am working right now." — actions happening now
Present Perfect: "I have completed the project." — past with present relevance
Simple Past: "I finished the report yesterday." — completed past action
Past Continuous: "I was preparing when the call came." — interrupted past action
Future Simple: "I will present tomorrow." — definite future
Future Perfect: "I will have submitted it by Friday." — completed future action
→ Always give 2-3 examples, then say: "Now you try — make your own sentence using this tense!"

ARTICLES (a / an / the):
"a" before consonant sounds: a university, a car, a team
"an" before vowel sounds: an apple, an hour, an MBA
"the" for specific/known things: the manager called, the report is ready
No article for general plurals/uncountables: "Dogs are loyal", "Water is essential"
Common Indian English errors: "I went to market" → "I went to the market"

PREPOSITIONS (common Indian English mistakes):
"discuss about" → "discuss" (discuss already implies 'about')
"reach to" → "reach" (reach is transitive)
"cope up with" → "cope with"
"revert back" → "revert" (revert already means go back)
"I am having a meeting" → "I have a meeting" (state verbs not used in continuous)

SUBJECT-VERB AGREEMENT:
"He go" → "He goes" (third person singular -s)
"The data are" vs "The data is" (both acceptable; corporate: "is")
"Neither of them are" → "Neither of them is"

VOCABULARY UPGRADES (always give in context):
basically → fundamentally / in essence
stuff → aspects / components / elements
I think → I believe / In my assessment / From my perspective
ok/yeah → certainly / absolutely / indeed
guys → colleagues / team members
got → received / obtained / achieved
want → aspire to / aim to / intend to
hard work → diligence / perseverance / dedication
good at → proficient in / adept at / skilled in
help → facilitate / assist / support
problem → challenge / obstacle
show → demonstrate / showcase / exhibit
very good → exceptional / outstanding / exemplary

FILLER WORDS to eliminate: "um", "uh", "like", "you know", "basically", "actually", "right?" — point out gently and give restructured sentence

INTERVIEW COACHING:
STAR Method for behavioral questions: Situation → Task → Action → Result
Self-introduction: Name → Education → Skills/Experience → Career Goals → Why this company
Confidence language: "I am confident that..." / "I have successfully..." / "My key strength is..."
Avoid self-deprecation: "I'm not sure but..." → "In my understanding..."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE PATTERN (always follow):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. RESPOND naturally to what was said (like a real conversation)
2. CORRECT gently if there was a grammar/vocab error
3. EXPLAIN the rule if it helps learning
4. INVITE — end with a question or prompt to keep going

RULES:
- Never just correct without responding to content
- If sentence is perfect → compliment and ask a follow-up question
- If student asks to practice interviews → ask interview questions one at a time
- If student asks to practice tenses → teach tense, give examples, ask student to try
- 3-5 sentences max in response (TTS-friendly, no bullet points in response field)
- coaching_tip: quote exact error → corrected version → brief reason (or praise if correct)"""

            # ── BUILD MESSAGES WITH CONVERSATION HISTORY ──
            messages = [{"role": "system", "content": system_prompt}]

            # Add recent history for context (last 20 turns = 10 exchanges)
            recent_history = history[-20:] if len(history) > 20 else history
            for turn in recent_history[:-1]:  # all but current message (already in user_text)
                role = turn.get('role', 'user')
                content = turn.get('content', '')
                if role in ('user', 'assistant') and content:
                    messages.append({"role": role, "content": content})

            # Current user message with JSON instruction embedded
            messages.append({
                "role": "user",
                "content": f"""{user_text}

[SYSTEM: Respond ONLY with this JSON, no extra text, no markdown fences:]
{{
  "response": "Your warm natural reply (3-5 sentences, TTS-ready). Respond to content first, correct/teach second, always end with question or prompt.",
  "coaching_tip": "If error found: 'You said [exact phrase] — better: [corrected version]. Reason: [one line]'. If perfect: 'Excellent! Your sentence was grammatically correct and professional.' If teaching: summarize key rule in one sentence.",
  "score": <integer 0-100>
}}"""
            })

            # Call OpenAI directly with messages (not via openai_generate wrapper)
            try:
                api_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=600,
                    temperature=0.75,
                )
                raw = api_response.choices[0].message.content
            except Exception as api_err:
                print(f"OpenAI API error: {api_err}")
                raw = None

            # ── ROBUST JSON EXTRACTION ──
            result = None
            if raw:
                raw = raw.strip()
                # Direct parse
                try:
                    result = json.loads(raw)
                except Exception:
                    pass

                # Extract from code block
                if result is None and "```" in raw:
                    for part in raw.split("```"):
                        part = part.strip()
                        if part.startswith("json"):
                            part = part[4:].strip()
                        try:
                            parsed = json.loads(part)
                            if "response" in parsed:
                                result = parsed
                                break
                        except Exception:
                            continue

                # Regex extract JSON object
                if result is None:
                    import re
                    match = re.search(r'\{[\s\S]*?"response"[\s\S]*?\}', raw)
                    if match:
                        try:
                            result = json.loads(match.group())
                        except Exception:
                            pass

            if result is None:
                print("JSON PARSE FAILED. RAW:", raw)
                result = {
                    "response": "I heard you! Could you say that again more clearly so I can give you the best feedback?",
                    "coaching_tip": "Speak in complete, clear sentences for accurate evaluation.",
                    "score": 70
                }

            # ── SAVE TURN TO DB ──
            CommunicationTurn.objects.create(
                session=session,
                user_text=user_text,
                ai_text=result.get('response', ''),
                coaching_feedback=result.get('coaching_tip', ''),
                score=result.get('score', 70)
            )

            # Update session running average score
            turns = session.turns.all()
            if turns.exists():
                all_scores = [t.score for t in turns if t.score is not None]
                if all_scores:
                    session.score = int(sum(all_scores) / len(all_scores))
                    session.save()

            return JsonResponse({
                'status': 'success',
                'session_id': session.id,
                'ai_response': result.get('response', ''),
                'coaching_tip': result.get('coaching_tip', ''),
                'score': result.get('score', 0)
            })

        except Exception as e:
            print("COMM_AGENT_ERROR:", e)
            import traceback
            traceback.print_exc()
            error_msg = str(e).lower()
            if "429" in error_msg or "rate" in error_msg or "exhausted" in error_msg:
                return JsonResponse({
                    'status': 'error',
                    'message': 'The AI Coach is taking a short break (API limit reached). Please try again in a few minutes.'
                }, status=429)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)



@csrf_exempt
@login_required
def generate_vocab(request):
    if request.method == 'GET':
        # Get recently shown words from frontend to avoid repeats
        exclude_param = request.GET.get('exclude', '')
        exclude_words = [w.strip() for w in exclude_param.split(',') if w.strip()]

        # High-entropy seed — different every single call
        seed = random.randint(100000, 9999999)
        
        avoid_clause = ''
        if exclude_words:
            avoid_clause = f"Do NOT use any of these words: {', '.join(exclude_words)}."

        prompt = f"""
You are a Vocabulary Master. Generate exactly one UNIQUE advanced professional vocabulary word.

SEED (use this to vary your response): {seed}
{avoid_clause}

Rules:
- Pick a genuinely different word each time.
- It must be suitable for corporate/professional communication.
- The word must NOT be a common everyday word.

Return ONLY valid JSON in this exact format, no markdown, no backticks, no extra text:
{{
  "word": "Word",
  "pronunciation": "/prəˌnʌnsiˈeɪʃən/",
  "meaning": "Clear meaning of the word.",
  "example": "A professional example sentence using the word."
}}
"""
        try:
            raw = openai_generate(prompt)
            if not raw:
                raise Exception("No response from AI")
            raw = raw.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            return JsonResponse({'status': 'success', 'data': data})
        except Exception as e:
            print("Generate Vocab Error:", e)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)


@csrf_exempt
@login_required
def check_grammar(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            sentence = body.get('sentence', '').strip()
            if not sentence:
                return JsonResponse({'status': 'error', 'message': 'No sentence provided'})

            prompt = f"""
            You are a Grammar Guru. Analyze the following sentence and correct any grammatical errors. If the sentence is already perfect, suggest a more professional alternative.
            Sentence: "{sentence}"
            
            Return ONLY valid JSON in this exact format, no markdown, no backticks:
            {{
              "fixed_text": "The corrected or improved sentence.",
              "explanation": "A brief explanation of what was changed or improved."
            }}
            """
            raw = openai_generate(prompt)
            if not raw:
                raise Exception("No response from AI")
            raw = raw.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            return JsonResponse({'status': 'success', 'data': data})
        except Exception as e:
            print("Check Grammar Error:", e)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)
