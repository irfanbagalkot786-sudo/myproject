from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.management import call_command

from .forms import LoginForm, StudentProfileForm
from .models import StudentProfile, Skill, StudentSkill, Project, Resume, ResumeAnalysis, Company, JobRole, Recommendation, Question

import os
import subprocess
import json
import time
import fitz  # pymupdf
import base64
import google.generativeai as genai
import PyPDF2
import whisper
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from .models import InterviewSession
from django.http import HttpResponse

# ─── Config ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyD6ClT2cU6zIS7Tu1thWyG3nrvF5a-15uA"
GEMINI_MODEL   = "gemini-2.5-flash-lite"   # ✅ working model
# ────────────────────────────────────────────────────────────────────────────

#----------whispermodel---------

model = None

def get_model():
    global model
    if model is None:
        import whisper
        model = whisper.load_model("small")
    return model

def your_view(request):
    model = get_model()


def gemini_generate(prompt_or_parts):
    """
    Call Gemini with automatic retry (3 attempts, 10s apart).
    Accepts either a string prompt or a list of parts (for vision).
    """
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    last_error = None
    for attempt in range(3):
        try:
            response = model.generate_content(prompt_or_parts)
            return response
        except Exception as e:
            last_error = e
            print(f"Gemini attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                print(f"Retrying in 10 seconds...")
                time.sleep(10)

    raise last_error  # re-raise after all retries exhausted


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
    student = request.user.studentprofile  # or however you fetch it
    student_skills = student.studentskill_set.all()
    all_skills = Skill.objects.all()
    return render(request, 'dashboard.html', {
        'student': student,
        'student_skills': student_skills,
        'all_skills': all_skills,
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
        messages.success(request, 'Profile updated successfully!')
        return redirect('student_profile')

    student_skills = StudentSkill.objects.filter(student=student).select_related('skill')
    context = {
        'student':           student,
        'student_skills':    student_skills,
        'student_languages': student.get_languages_list(),
    }
    return render(request, 'student_profile.html', context)

# ================= REMOVE PHOTO  =================

def remove_photo(request):
        if request.method == "POST":
            student = request.user.studentprofile  # adjust if needed
            student.profile_photo.delete(save=True)
        return redirect('student_profile')


# ================= UPDATE PHOTO  =================

def update_photo(request):
    if request.method == "POST":
        student = request.user.studentprofile  # adjust if needed

        if 'profile_photo' in request.FILES:
            student.profile_photo = request.FILES['profile_photo']
            student.save()

    return redirect('student_profile')

# ================= DELETE SKILL  =================

def delete_skill(request, skill_id):
    student = request.user.studentprofile  # ✅ correct relation

    skill = get_object_or_404(StudentSkill, id=skill_id, student=student)
    skill.delete()

    return redirect('student_profile')

#================== ADD SKILL  =================

def add_skill_profile(request):
    if request.method == "POST":
        student, _ = StudentProfile.objects.get_or_create(user=request.user)

        skill_id = request.POST.get("skill_id")
        proficiency = request.POST.get("proficiency", "beginner")

        if skill_id:
            skill = Skill.objects.get(id=skill_id)

            StudentSkill.objects.create(
                student=student,
                skill=skill,
                proficiency_level=proficiency
            )

    return redirect('student_profile')

# ================= SKILLS VIEW =================

@login_required
def skills_view(request):
    student, _ = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': request.user.username}
    )

    if request.method == 'POST':
        skill_id = request.POST.get('skill')
        level    = request.POST.get('level')

        if not skill_id or not level:
            messages.error(request, 'Please select both a skill and a level.')
            return redirect('skills')

        skill    = get_object_or_404(Skill, id=skill_id)
        obj, created = StudentSkill.objects.get_or_create(
            student=student, skill=skill, defaults={'level': level}
        )
        if created:
            messages.success(request, f'"{skill.name}" added successfully!')
        else:
            obj.level = level
            obj.save()
            messages.info(request, f'"{skill.name}" level updated to {level}.')
        return redirect('skills')

    all_skills     = Skill.objects.all().order_by('category', 'name')
    student_skills = StudentSkill.objects.filter(student=student).select_related('skill')
    return render(request, 'skills.html', {'skills': all_skills, 'student_skills': student_skills})


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
            data  = json.loads(request.body)
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


# ================= PDF → BASE64 IMAGES HELPER =================

def pdf_to_base64_images(file):
    file.seek(0)
    pdf_bytes = file.read()
    doc       = fitz.open(stream=pdf_bytes, filetype="pdf")
    images    = []
    for page in doc:
        mat       = fitz.Matrix(2, 2)
        pix       = page.get_pixmap(matrix=mat)
        b64       = base64.b64encode(pix.tobytes("png")).decode("utf-8")
        images.append(b64)
    print(f"PDF CONVERTED: {len(images)} page(s) → base64 images")
    return images


# ================= UPLOAD RESUME =================

@login_required
def upload_resume(request):
    if request.method == "POST":
        file = request.FILES.get('resume')
        print("=== UPLOAD RESUME CALLED ===")

        if not file:
            messages.error(request, "Please select a file.")
            return redirect('upload_resume')

        print("FILE NAME:", file.name)

        # Save resume to DB
        try:
            resume = Resume.objects.create(student=request.user.studentprofile, file=file)
            print("RESUME SAVED:", resume.id)
        except Exception as e:
            print("SAVE ERROR:", e)
            messages.error(request, f"Save error: {e}")
            return redirect('upload_resume')

        # ✅ Prevent duplicate API calls — reuse existing analysis if score > 0
        existing = ResumeAnalysis.objects.filter(resume=resume).first()
        if existing and existing.analysis_score > 0:
            print("REUSING EXISTING ANALYSIS")
            messages.success(request, "Resume already analyzed!")
            return redirect('analyze_resume')

        # Decide: Vision (PDF) vs Text (DOCX)
        use_vision = file.name.lower().endswith('.pdf')

        if use_vision:
            try:
                page_images = pdf_to_base64_images(file)
            except Exception as e:
                print("PDF→IMAGE ERROR:", e)
                messages.error(request, f"Could not convert PDF: {e}")
                return redirect('upload_resume')
        else:
            try:
                file.seek(0)
                resume_text = file.read().decode('utf-8', errors='ignore')
                print("TEXT EXTRACTED, length:", len(resume_text))
                if not resume_text.strip():
                    resume_text = "No text could be extracted from this resume."
            except Exception as e:
                print("TEXT EXTRACT ERROR:", e)
                messages.error(request, f"Could not read file: {e}")
                return redirect('upload_resume')

        # ✅ Call Gemini with retry
        json_instruction = """
Analyze this resume and return ONLY valid JSON, no extra text, no backticks.

Return exactly:
{
    "score": <number 0-100>,
    "feedback": "<detailed feedback about layout, content, and improvements>",
    "recommended_roles": ["role1", "role2", "role3"]
}
"""
        try:
            print(f"CALLING GEMINI ({GEMINI_MODEL})...")

            if use_vision:
                parts = [
                    {"inline_data": {"mime_type": "image/png", "data": img}}
                    for img in page_images
                ]
                parts.append({"text": json_instruction})
                response = gemini_generate(parts)
            else:
                prompt   = f"Analyze this resume:\n{resume_text[:3000]}\n\n{json_instruction}"
                response = gemini_generate(prompt)

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
            messages.error(request, f"AI response parse error: {e}")
            return redirect('upload_resume')
        except Exception as e:
            print("GEMINI ERROR:", e)
            messages.error(request, f"Gemini error: {e}")
            return redirect('upload_resume')

        # Save analysis to DB
        try:
            analysis, _             = ResumeAnalysis.objects.get_or_create(resume=resume)
            analysis.analysis_score = data.get('score', 0)
            analysis.feedback       = data.get('feedback', 'No feedback.')
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

    # Read PDF text
    resume_text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(resume_obj.file.path)
        for page in pdf_reader.pages:
            resume_text += page.extract_text()
    except Exception as e:
        print(f"PDF Reader Error: {e}")
        resume_text = "Could not parse PDF content."

    # ✅ Call Gemini with retry
    try:
        prompt = f"""
Analyze this resume text and provide exactly 4 things in JSON format:
1. "skills": A list of technical skills found (e.g. ["Python", "Django", "React"]).
2. "experience_years": A number representing total years of experience.
3. "score": A match score out of 100 for a general SDE role.
4. "feedback": A 2-sentence summary of strengths and areas to improve.

Resume Text:
{resume_text[:4000]}
"""
        response = gemini_generate(prompt)

        raw_text = response.text.strip()
        json_str = raw_text
        if "```json" in raw_text:
            json_str = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            json_str = raw_text.split("```")[1].split("```")[0].strip()

        data = json.loads(json_str)

        analysis, _ = ResumeAnalysis.objects.update_or_create(
            resume=resume_obj,
            defaults={
                'experience_years': data.get('experience_years', 0),
                'analysis_score':   data.get('score', 0),
                'feedback':         data.get('feedback', '')
            }
        )

        for s_name in data.get('skills', []):
            skill_obj, _ = Skill.objects.get_or_create(name=s_name.strip().title())
            analysis.extracted_skills.add(skill_obj)
            StudentSkill.objects.get_or_create(student=student, skill=skill_obj)

    except Exception as e:
        print(f"Gemini Error: {e}")
        analysis, _ = ResumeAnalysis.objects.update_or_create(
            resume=resume_obj,
            defaults={
                'analysis_score': 0,
                'feedback': "Could not analyze resume. Please ensure the file is readable."
            }
        )

    return render(request, "upload_resume.html", {'analysis': analysis, 'student': student})


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
    return render(request, 'recommendations.html', {'recommendations': recs})


@login_required
def recommendations_view(request):
    student = request.user.studentprofile
    recs    = Recommendation.objects.filter(student=student).order_by('-match_percentage')
    return render(request, "recommendations.html", {'recommendations': recs})


@login_required
def generate_recommendations(request):
    student        = request.user.studentprofile
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

    messages.success(request, f"Generated {roles.count()} recommendations based on your profile!")
    return redirect('recommendations')


def company_details(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    return render(request, "company_details.html", {'company': company})


# ================= VIRTUAL INTERVIEW =================

@login_required
def virtual_interview(request):
    company_name = request.GET.get('company', 'General')
    interview_type = request.GET.get('type', 'hr')
    return render(request, 'virtual_interview.html', {'company_name': company_name, 'interview_type': interview_type})

@csrf_exempt
@login_required
def generate_tech_questions(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            language = data.get('language', 'Python')
            prompt = f"Generate exactly 9 technical interview questions for a candidate specializing in {language}. Return ONLY valid JSON as a list of strings: [\"question 1\", \"question 2\", ...]"
            
            response = gemini_generate(prompt)
            raw = response.text.strip()
            
            # Clean markdown
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

#============perform_full_interview_analysis=======

def perform_full_interview_analysis(interview):
    """Helper to run the complete AI analysis pipeline automatically."""
    print(f"🎬 Starting automatic analysis for Interview ID: {interview.id}")
    
    # 1. Extract Audio
    audio_path = extract_audio_from_video(interview.video_file)
    if not audio_path:
        print("❌ Audio extraction failed during automatic processing")
        return False

    # 2. Transcribe with Whisper
    print("🎤 Transcribing...")
    whisper_model = get_model()
    result = whisper_model.transcribe(audio_path)
    transcript = result.get("text", "")
    interview.transcript = transcript
    print(f"📝 Transcript length: {len(transcript)}")

    # 3. Analyze with Gemini
    print("🧠 Analyzing with Gemini...")
    analysis = analyze_transcript(transcript)
    
    content_score = analysis.get("score", 70)
    confidence_score = interview.confidence_score
    eye_contact_score = interview.eye_contact_score
    
    # Weighted Score Calculation
    final_score = int((content_score * 0.6) + (confidence_score * 0.2) + (eye_contact_score * 0.2))

    interview.ai_score = max(0, min(100, final_score))
    interview.ai_feedback = f"{analysis.get('feedback', '')} \n\nBehavioral Analysis: {analysis.get('behavioral_feedback', 'Processed automatically.')}"
    
    strengths = analysis.get("strengths")
    weaknesses = analysis.get("weaknesses")

    if not strengths:
        strengths = ["Good communication", "Willing to answer", "Basic understanding"]
    if not weaknesses:
        weaknesses = ["Needs more clarity", "Lack of examples", "Short answers"]

    interview.strengths = json.dumps(strengths)
    interview.weaknesses = json.dumps(weaknesses)

    # ✅ THIS WAS MISSING — save everything to the database
    interview.save()

    print("✅ Strengths:", strengths)
    print("✅ Weaknesses:", weaknesses)
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

            # ✅ AI Analysis with behavioral context
            try:
                prompt = f"""
Analyze this interview for {company_name}. 
The candidate had the following behavioral metrics captured in real-time:
- Confidence Score: {confidence_score}%
- Eye Contact Score: {eye_contact_score}%

Provide an evaluation based on the candidate's performance. Consider both behavioral metrics and the likely content of an interview for this company.

Return ONLY valid JSON:
{{
  "content_score": 0-100,
  "behavioral_feedback": "specifically about confidence and eye contact",
  "general_feedback": "overall performance and suggestions",
  "transcript": "suggested transcript summary"

  "strengths": ["point1", "point2", "point3"],
  "weaknesses": ["point1", "point2", "point3"]
}}
"""
                response = gemini_generate(prompt)
                raw = response.text.strip()
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                data = json.loads(raw.strip())

                # Weighted Score Calculation
                # 60% Content, 20% Confidence, 20% Eye Contact
                content_score = data.get('content_score', 70)
                final_score = int((content_score * 0.6) + (confidence_score * 0.2) + (eye_contact_score * 0.2))
                
                interview.ai_score    = max(0, min(100, final_score))
                interview.ai_feedback = f"{data.get('general_feedback', '')} \n\nBehavioral Analysis: {data.get('behavioral_feedback', '')}"
                interview.transcript  = data.get('transcript', 'Transcript summary generated.')
                interview.save()

            except Exception as e:
                print("AI ANALYSIS ERROR:", e)
                # Fallback weighted score if AI fails
                final_score = int((75 * 0.6) + (confidence_score * 0.2) + (eye_contact_score * 0.2))
                interview.ai_score    = final_score
                interview.ai_feedback = "AI analysis encountered an error, but your behavioral scores were factored in. Focus on clear articulation."
                interview.transcript  = "[Automated Summary due to analysis error]"
                interview.save()

            # 🔥 NEW: AUTOMATIC FULL PROCESSING (Transcription + Detailed Analysis)
            # This runs synchronously during the save. In a production app, this would be a background task (Celery).
            perform_full_interview_analysis(interview)

            return JsonResponse({'status': 'success', 'message': 'Interview saved and processed!', 'id': interview.id})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})



def extract_audio_from_video(video_field):
    try:
        # Step 1: Get full video path
        video_path = video_field.path   # VERY IMPORTANT

        # Step 2: Create output audio path
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_filename = base_name + ".wav"
        
        audio_folder = os.path.join(settings.MEDIA_ROOT, "audio")
        os.makedirs(audio_folder, exist_ok=True)

        audio_path = os.path.join(audio_folder, audio_filename)

        # Step 3: FFmpeg command
        command = [
            "ffmpeg",
            "-i", video_path,
            "-vn",              # no video
            "-acodec", "pcm_s16le",  # high quality WAV
            "-ar", "16000",
            "-ac", "1",
            audio_path
        ]

        # Step 4: Run command
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


# ================= Transcript Analyze =================
def analyze_transcript(transcript):
    import json

    prompt = f"""
You are an expert HR interviewer.

Analyze the following interview transcript.

Transcript:
{transcript}

INSTRUCTIONS:
- Always return at least 3 strengths
- Always return at least 3 weaknesses
- Be specific and meaningful
- Do NOT return empty lists

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "score": number between 0-100,
  "strengths": ["point1", "point2", "point3"],
  "weaknesses": ["point1", "point2", "point3"],
  "feedback": "detailed feedback"
}}
"""

    response = gemini_generate(prompt)
    raw = response.text.strip()

    # Clean markdown
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    print("🔥 RAW GEMINI RESPONSE:", raw)  # DEBUG

    data = json.loads(raw.strip())

    return data

@login_required
def interview_results(request):
    try:
        # Temporary trigger to apply pending migrations
        call_command('migrate', interactive=False)
    except Exception as e:
        print(f"Migration error: {e}")
    student    = request.user.studentprofile
    interviews = InterviewSession.objects.filter(student=student).order_by('-created_at')
    return render(request, 'interview_results.html', {'interviews': interviews})

#=====interview details====================

@login_required
def interview_detail(request, interview_id):
    interview = get_object_or_404(
        InterviewSession, id=interview_id, student=request.user.studentprofile
    )
    
    # Parse strengths and weaknesses from JSON strings
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
