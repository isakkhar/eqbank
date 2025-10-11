from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from core.forms import SignUpForm, BANGLADESH_DIVISIONS_DISTRICTS_THANAS, QuestionPaperForm
from .models import Profile, ClassName, Subject, Chapter, QuestionPaper
from .models import Question

from django.views.decorators.http import require_POST
from django.db.models import Q



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
def teacher_question_select(request):
    """Teacher view: filter questions by class/subject/chapter and select many to include in a paper."""
    classes = ClassName.objects.all()
    subjects = Subject.objects.none()
    chapters = Chapter.objects.none()
    questions = Question.objects.none()
    show_questions = False

    if request.method == 'GET':
        class_id = request.GET.get('class_id')
        subject_id = request.GET.get('subject_id')
        chapter_id = request.GET.get('chapter_id')
        question_type = request.GET.get('question_type')
        question_count = request.GET.get('question_count')

        # Dropdown population logic (unchanged)
        if class_id:
            subjects = Subject.objects.filter(class_name_id=class_id)
        if subject_id:
            chapters = Chapter.objects.filter(subject_id=subject_id)
        
        # --- মূল পরিবর্তন এখানে ---
        # প্রশ্ন দেখানোর জন্য এখন ক্লাস, বিষয়, অধ্যায় এবং প্রশ্নের ধরন সবগুলোই আবশ্যক
        if class_id and subject_id and chapter_id and question_type:
            show_questions = True
            
            # ফিল্টার তৈরির সময় chapter_id সরাসরি অন্তর্ভুক্ত করা হয়েছে
            q_filters = {
                'class_name_id': class_id,
                'subject_id': subject_id,
                'chapter_id': chapter_id,  # chapter_id এখন আবশ্যিক ফিল্টার
                'question_type': question_type,
            }

            questions = Question.objects.filter(**q_filters).order_by('-created_at')
            
            # ব্যবহারকারীর ইনপুট অনুযায়ী প্রশ্নের সংখ্যা সীমাবদ্ধ করা
            if question_count:
                try:
                    count = int(question_count)
                    if count > 0:
                        questions = questions[:count]
                except (ValueError, TypeError):
                    questions = questions[:20]  # Default to 20 if input is invalid

    return render(request, 'core/teacher_select_questions.html', {
        'classes': classes,
        'subjects': subjects,
        'chapters': chapters,
        'questions': questions,
        'show_questions': show_questions,
    })


@login_required
def prepare_paper_view(request):
    """Receive selected question ids and render a printable view with school name, time and marks.
    Optionally include an OMR bubble area if requested.
    """
    if request.method == 'POST':
        q_ids = request.POST.getlist('question_ids')
        school_name = request.POST.get('school_name')
        duration = request.POST.get('duration')
        total_marks = request.POST.get('total_marks')
        include_omr = request.POST.get('include_omr') == 'on'

        questions = Question.objects.filter(id__in=q_ids)

        # If no questions selected, don't create an empty paper — redirect back
        if not questions.exists():
            return redirect('teacher_select_questions')

        # Persist the prepared paper to the database so every prepared paper is recorded
        paper = QuestionPaper.objects.create(
            program_name=f"Prepared: {school_name or 'Paper'}",
            creator=request.user,
            class_level=questions.first().class_name if questions.exists() else ClassName.objects.first(),
            question_type='combined' if questions.exists() else 'mcq',
            number_of_questions=questions.count()
        )
        # attach selected questions
        paper.questions.set(questions)

        context = {
            'school_name': school_name,
            'duration': duration,
            'total_marks': total_marks,
            'include_omr': include_omr,
            'questions': questions,
            'paper': paper,
            'show_answers': True,
        }
        return render(request, 'core/prepare_paper.html', context)

    return redirect('teacher_select_questions')

@login_required
def question_ready(request):
    return render(request, template_name='core/question_ready.html')

@login_required
def my_papers_list(request):
    """Display all question papers created by the current user in a table with pagination"""
    papers_list = QuestionPaper.objects.filter(creator=request.user).order_by('-created_at')
    
    # Pagination: 10 papers per page
    paginator = Paginator(papers_list, 10)
    page_number = request.GET.get('page', 1)
    
    try:
        papers = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        papers = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        papers = paginator.page(paginator.num_pages)
    
    return render(request, 'core/my_papers_list.html', {'papers': papers})

@login_required
def paper_delete_view(request, paper_id):
    """Delete a specific paper created by the current user"""
    try:
        paper = QuestionPaper.objects.get(id=paper_id, creator=request.user)
        paper.delete()
        return JsonResponse({'success': True, 'message': 'পেপার সফলভাবে মুছে ফেলা হয়েছে'})
    except QuestionPaper.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'পেপার পাওয়া যায়নি'}, status=404)

@login_required
def paper_detail_view(request, paper_id):
    """Display a specific paper in A4 format for viewing/printing"""
    try:
        paper = QuestionPaper.objects.get(id=paper_id, creator=request.user)
    except QuestionPaper.DoesNotExist:
        return redirect('my_papers_list')
    
    questions = paper.questions.all()
    
    context = {
        'paper': paper,
        'questions': questions,
        'school_name': paper.program_name,
        'total_marks': paper.number_of_questions * 1,  # Assuming 1 mark per question
        'duration': '60 মিনিট',  # Default duration
    }
    return render(request, 'core/paper_detail_a4.html', context)


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


@login_required
@require_POST
def create_question_from_modal(request):
    """Create question(s) from the modal on the teacher select page.
    Accepts multipart/form-data with fields:
      - class_id (required)
      - text (required)
      - question_type
      - option_a..option_d
      - correct_option
      - subjects (optional, multiple)
      - chapters (optional, multiple)

    Returns JSON {created: n, errors: [..]}.
    """
    class_id = request.POST.get('class_id') or request.POST.get('class')
    if not class_id:
        return JsonResponse({'error': 'class_id is required'}, status=400)

    try:
        class_obj = ClassName.objects.get(id=int(class_id))
    except (ClassName.DoesNotExist, ValueError):
        return JsonResponse({'error': 'invalid class'}, status=400)

    text = (request.POST.get('text') or '').strip()
    if not text:
        return JsonResponse({'error': 'question text is required'}, status=400)

    question_type = request.POST.get('question_type') or 'mcq'
    option_a = request.POST.get('option_a') or None
    option_b = request.POST.get('option_b') or None
    option_c = request.POST.get('option_c') or None
    option_d = request.POST.get('option_d') or None
    correct_option = (request.POST.get('correct_option') or '').strip() or None

    subjects = request.POST.getlist('subjects')
    chapters = request.POST.getlist('chapters')

    # If no multi selections provided, try to fallback to the current filters (subject/chapter fields)
    if not subjects:
        cur_subj = request.POST.get('subject_id') or request.GET.get('subject_id')
        if cur_subj:
            subjects = [cur_subj]
    if not chapters:
        cur_chap = request.POST.get('chapter_id') or request.GET.get('chapter_id')
        if cur_chap:
            chapters = [cur_chap]

    subj_qs = Subject.objects.filter(id__in=subjects, class_name=class_obj) if subjects else None
    chap_qs = Chapter.objects.filter(id__in=chapters) if chapters else None

    created = 0
    errors = []

    # Create per combinations similar to admin behavior
    try:
        if subj_qs and chap_qs:
            for s in subj_qs:
                for ch in chap_qs.filter(subject_id=s.id):
                    Question.objects.create(
                        text=text,
                        question_type=question_type,
                        class_name=class_obj,
                        subject=s,
                        chapter=ch,
                        option_a=option_a,
                        option_b=option_b,
                        option_c=option_c,
                        option_d=option_d,
                        correct_option=correct_option
                    )
                    created += 1
        elif subj_qs:
            for s in subj_qs:
                Question.objects.create(
                    text=text,
                    question_type=question_type,
                    class_name=class_obj,
                    subject=s,
                    chapter=None,
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c,
                    option_d=option_d,
                    correct_option=correct_option
                )
                created += 1
        elif chap_qs:
            for ch in chap_qs:
                Question.objects.create(
                    text=text,
                    question_type=question_type,
                    class_name=class_obj,
                    subject=ch.subject,
                    chapter=ch,
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c,
                    option_d=option_d,
                    correct_option=correct_option
                )
                created += 1
        else:
            # no subjects/chapters provided — create single question in no-subject state (not ideal)
            Question.objects.create(
                text=text,
                question_type=question_type,
                class_name=class_obj,
                subject=None,
                chapter=None,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_option=correct_option
            )
            created = 1
    except Exception as e:
        errors.append(str(e))

    return JsonResponse({'created': created, 'errors': errors})


@login_required
@require_POST
def delete_paper(request, paper_id):
    try:
        # সঠিক মডেল (QuestionPaper) এবং সঠিক ফিল্ড (creator) ব্যবহার করুন
        paper = get_object_or_404(QuestionPaper, id=paper_id, creator=request.user)
        paper.delete()

        return JsonResponse({
            'success': True,
            'message': 'পেপারটি সফলভাবে মুছে ফেলা হয়েছে।'
        })
    except QuestionPaper.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'পেপারটি খুঁজে পাওয়া যায়নি বা আপনার এটি মুছে ফেলার অনুমতি নেই।'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'একটি সমস্যা হয়েছে: {str(e)}'
        }, status=500)
