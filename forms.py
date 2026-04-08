from django import forms


# ================= LOGIN FORM =================
# Captcha is handled entirely on the frontend (JS canvas).
# No captcha field or import needed here.

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your username',
            'autocomplete': 'off',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
        })
    )


# ================= STUDENT PROFILE FORM =================

class StudentProfileForm(forms.Form):
    full_name       = forms.CharField(max_length=200, required=False)
    college         = forms.CharField(max_length=200, required=False)
    branch          = forms.CharField(max_length=50,  required=False)
    cgpa            = forms.FloatField(required=False, min_value=0, max_value=10)
    graduation_year = forms.IntegerField(required=False)
    phone           = forms.CharField(max_length=15, required=False)
    linkedin_url    = forms.URLField(required=False)
    github_url      = forms.URLField(required=False)
    work_mode       = forms.CharField(max_length=10, required=False)
