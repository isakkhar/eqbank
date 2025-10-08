from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, redirect

from core.forms import SignUpForm, BANGLADESH_DIVISIONS_DISTRICTS_THANAS, QuestionPaperForm
from .models import Profile, ClassName, Subject, Chapter, QuestionPaper


# Create your views here.
def landing_page(request):
    return render(request, template_name='landing_page.html')


# Signup View
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)

        # সাবমিট করার সময় জেলা ও থানার তালিকা লোড করা (ভ্যালিডেশনের জন্য)
        selected_division = request.POST.get('division')
        selected_district = request.POST.get('district')

        if selected_division:
            districts = BANGLADESH_DIVISIONS_DISTRICTS_THANAS.get(selected_division, {}).keys()
            district_choices = [('', '----- জেলা নির্বাচন করুন -----')] + [(district, district) for district in
                                                                           districts]
            form.fields['district'].choices = district_choices

        if selected_division and selected_district:
            thanas = BANGLADESH_DIVISIONS_DISTRICTS_THANAS.get(selected_division, {}).get(selected_district, [])
            thana_choices = [('', '----- থানা নির্বাচন করুন -----')] + [(thana, thana) for thana in thanas]
            form.fields['thana'].choices = thana_choices

        if form.is_valid():
            cd = form.cleaned_data
            new_user = User.objects.create_user(username=cd['username'], password=cd['password'])
            Profile.objects.create(
                user=new_user,
                division=cd['division'],
                district=cd['district'],
                thana=cd['thana']
            )
            login(request, new_user)
            return redirect('dashboard')
    else:
        form = SignUpForm()

    # ফর্মের ফিল্ডগুলোতে CSS ক্লাস যোগ করা
    for field_name, field in form.fields.items():
        field.widget.attrs.update({'class': 'form-control'})

    return render(request, 'users/signup.html', {'form': form})


# AJAX View for loading districts
def load_districts(request):
    division = request.GET.get('division')
    districts = list(BANGLADESH_DIVISIONS_DISTRICTS_THANAS.get(division, {}).keys())
    return JsonResponse(districts, safe=False)


# AJAX View for loading thanas
def load_thanas(request):
    division = request.GET.get('division')
    district = request.GET.get('district')
    thanas = []
    if division and district:
        thanas = BANGLADESH_DIVISIONS_DISTRICTS_THANAS.get(division, {}).get(district, [])
    return JsonResponse(thanas, safe=False)


# Login View
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})


# Logout View
def logout_view(request):
    logout(request)
    return redirect('landing_page')  # Redirect to login page after logout


# Dashboard View - Protected
@login_required
def dashboard_view(request):
    return render(request, 'core/dashboard.html')


@login_required
def question_page(request):
    # Provide the QuestionPaperForm instance and classes queryset so the
    # template can render the class select and labels correctly.
    form = QuestionPaperForm()
    classes = ClassName.objects.all()
    return render(request, 'core/question.html', {'form': form, 'classes': classes})


@login_required
def question_bank(request):
    return render(request, template_name='core/question_bank.html')

@login_required
def question_ready(request):
    return render(request, template_name='core/question_ready.html')


@login_required
def create_paper_submit_view(request):
    """Processes the submitted question paper form data."""
    if request.method == 'POST':
        form = QuestionPaperForm(request.POST)

        # ভ্যালিডেশনের জন্য সাবজেক্ট এবং চ্যাপ্টারের queryset লোড করা
        class_id = request.POST.get('class_level')
        if class_id:
            # Subject model uses `class_name` FK
            form.fields['subjects'].queryset = Subject.objects.filter(class_name_id=class_id)

        subject_ids_str = request.POST.get('subjects')
        if subject_ids_str:
            subject_ids = [int(sid) for sid in subject_ids_str.split(',')]
            form.fields['chapters'].queryset = Chapter.objects.filter(subject_id__in=subject_ids)

        if form.is_valid():
            cleaned_data = form.cleaned_data

            paper = QuestionPaper.objects.create(
                program_name=cleaned_data['program_name'],
                creator=request.user,
                class_level=cleaned_data['class_level'],
                question_type=cleaned_data['question_type'],
                number_of_questions=cleaned_data['number_of_questions']
            )

            # ManyToMany ফিল্ডগুলোর জন্য .set() ব্যবহার করা হয়
            subjects_from_form = Subject.objects.filter(id__in=[int(i) for i in request.POST.getlist('subjects')])
            chapters_from_form = Chapter.objects.filter(id__in=[int(i) for i in request.POST.getlist('chapters')])

            paper.subjects.set(subjects_from_form)
            paper.chapters.set(chapters_from_form)

            # Redirect to the create page and show the created paper there
            return redirect(f"/accounts/create-paper/?created={paper.id}")
        else:
            print(form.errors)
            # যদি ফর্ম ভ্যালিড না হয়, তাহলে error সহ ফর্ম পেইজে ফেরত পাঠানো যেতে পারে
            # কিন্তু এর জন্য question_form_view-তে POST হ্যান্ডেল করতে হবে
            # আপাতত সহজ রাখার জন্য ড্যাশবোর্ডে রিডাইরেক্ট করা হলো
            return redirect('create_question_paper')

    return redirect('create_question_paper')


@login_required
def create_question_paper_view(request):
    """Render the question paper form on GET and handle submission by delegating to
    create_paper_submit_view on POST.
    """
    if request.method == 'POST':
        # reuse existing submit handler to avoid duplicating logic
        return create_paper_submit_view(request)

    form = QuestionPaperForm()
    created_paper = None
    created_id = request.GET.get('created')
    if created_id:
        try:
            created_paper = QuestionPaper.objects.get(id=int(created_id), creator=request.user)
        except QuestionPaper.DoesNotExist:
            created_paper = None
    return render(request, 'core/question_paper_form.html', {'form': form, 'created_paper': created_paper})


# ---------------------------------
# --- AJAX Helper Views ---
# ---------------------------------

def ajax_load_districts(request):
    """Provides a list of districts based on the selected division for AJAX calls."""
    division = request.GET.get('division')
    districts = list(BANGLADESH_DIVISIONS_DISTRICTS_THANAS.get(division, {}).keys())
    return JsonResponse(districts, safe=False)


def ajax_load_thanas(request):
    """Provides a list of thanas based on the selected division and district for AJAX calls."""
    division = request.GET.get('division')
    district = request.GET.get('district')
    thanas = []
    if division and district:
        thanas = BANGLADESH_DIVISIONS_DISTRICTS_THANAS.get(division, {}).get(district, [])
    return JsonResponse(thanas, safe=False)


def ajax_load_subjects(request):
    """Provides a list of subjects based on the selected class for AJAX calls."""
    class_id = request.GET.get('class_id')
    # Subject model uses `class_name` FK; filter by class_name_id
    subjects = Subject.objects.filter(class_name_id=class_id).values('id', 'name')
    return JsonResponse(list(subjects), safe=False)


def ajax_load_chapters(request):
    """Provides a list of chapters based on selected subjects for AJAX calls."""
    subject_ids_str = request.GET.get('subject_ids', '')
    if subject_ids_str:
        subject_ids = [int(sid) for sid in subject_ids_str.split(',')]
        # Chapter model uses `subject` FK; filter by subject_id
        chapters = Chapter.objects.filter(subject_id__in=subject_ids).values('id', 'name')
        return JsonResponse(list(chapters), safe=False)
    return JsonResponse([], safe=False)