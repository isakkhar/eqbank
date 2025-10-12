from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse

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
    """Require class, subject, chapter(s), question_type and question_count to show questions.
    Adds debug info and normalizes some common labels to internal keys (mcq/short/creative).
    """
    classes = ClassName.objects.all()
    subjects = Subject.objects.none()
    chapters = Chapter.objects.none()
    questions = Question.objects.none()
    show_questions = False
    debug = {}

    if request.method == 'GET':
        class_id = request.GET.get('class_id')
        subject_id = request.GET.get('subject_id')

        # Accept either single chapter_id or comma-separated chapter_ids
        chapter_ids_raw = request.GET.get('chapter_ids') or request.GET.get('chapter_id') or ''
        chapter_ids = [int(x) for x in str(chapter_ids_raw).split(',') if x.strip().isdigit()]

        question_type_raw = (request.GET.get('question_type') or '').strip()
        question_count_raw = request.GET.get('question_count')

        # --- normalize question type robustly using keyword matching ---
        def normalize_qtype(s):
            if not s:
                return ''
            s_low = s.strip().lower()
            # mcq variants (English + Bangla variants)
            mcq_keywords = ['mcq', 'multiple', 'multiple choice', 'multiple-choice', 'multiplechoice', 'বহু', 'বহুনির্বাচনী', 'বহু-নির্বাচনী', 'বহু নির্বাচনি']
            short_keywords = ['short', 'সংক্ষেপ', 'সংক্ষিপ্ত']
            creative_keywords = ['creative', 'সৃজন', 'সৃজনশীল']

            for kw in mcq_keywords:
                if kw in s_low:
                    return 'mcq'
            for kw in short_keywords:
                if kw in s_low:
                    return 'short'
            for kw in creative_keywords:
                if kw in s_low:
                    return 'creative'
            return s_low  # fallback to the lowercased raw value

        qtype_key = normalize_qtype(question_type_raw)

        # populate dropdowns
        if class_id:
            subjects = Subject.objects.filter(class_name_id=class_id)
        if subject_id:
            chapters = Chapter.objects.filter(subject_id=subject_id)

        debug['input'] = {
            'class_id': class_id,
            'subject_id': subject_id,
            'chapter_ids_raw': chapter_ids_raw,
            'chapter_ids_parsed': chapter_ids,
            'question_type_raw': question_type_raw,
            'question_type_key': qtype_key,
            'question_count_raw': question_count_raw,
        }

        # require all fields per your requirement (chapter_ids must be non-empty)
        if class_id and subject_id and chapter_ids and qtype_key:
            show_questions = True

            base_qs = Question.objects.filter(
                class_name_id=class_id,
                subject_id=subject_id,
                chapter_id__in=chapter_ids,
            )

            # build robust filter for question_type:
            from django.db.models import Q
            if qtype_key == 'mcq':
                # match known mcq variants in DB
                qfilter = Q(question_type__iexact='mcq') | Q(question_type__icontains='multiple') | Q(question_type__icontains='বহু')
                base_qs = base_qs.filter(qfilter)
            elif qtype_key == 'short':
                qfilter = Q(question_type__iexact='short') | Q(question_type__icontains='সংক্ষিপ্ত') | Q(question_type__icontains='সংক্ষেপ')
                base_qs = base_qs.filter(qfilter)
            elif qtype_key == 'creative':
                qfilter = Q(question_type__iexact='creative') | Q(question_type__icontains='সৃজন')
                base_qs = base_qs.filter(qfilter)
            else:
                # unknown key — try exact match (case-insensitive)
                base_qs = base_qs.filter(question_type__iexact=qtype_key)

            debug['counts'] = {
                'base_in_chapters': base_qs.count(),
                'total_in_selected_chapters': Question.objects.filter(chapter_id__in=chapter_ids).count(),
                'null_chapter_same_subject_class': Question.objects.filter(chapter__isnull=True, subject_id=subject_id, class_name_id=class_id).count()
            }

            try:
                count = int(question_count_raw) if question_count_raw else 20
            except (ValueError, TypeError):
                count = 20

            questions = base_qs.order_by('-created_at')[:max(1, count)]

    return render(request, 'core/teacher_select_questions.html', {
        'classes': classes,
        'subjects': subjects,
        'chapters': chapters,
        'questions': questions,
        'show_questions': show_questions,
    })


@login_required
def prepare_paper(request):
    """
    Handle selected questions and render prepare_paper page.
    Safely read question ids and optional form fields (school_name, duration, total_marks, include_omr).
    Also precompute Bengali indices for template (no templatetags required).
    """
    if request.method != 'POST':
        messages.error(request, "No questions submitted.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # Accept multiple checkbox values or a single comma-separated string (from POST or GET)
    qid_list = request.POST.getlist('question_ids')
    if not qid_list:
        raw = request.POST.get('question_ids') or request.POST.get('question_ids[]') or request.GET.get('question_ids', '') or ''
        if raw:
            qid_list = [s for s in raw.split(',') if s.strip().isdigit()]

    try:
        qids = [int(x) for x in qid_list]
    except (ValueError, TypeError):
        qids = []

    if not qids:
        messages.error(request, "কোনো প্রশ্ন নির্বাচিত হয়নি।")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # load questions with related fks
    from .models import Question
    questions_qs = Question.objects.filter(id__in=qids).select_related('class_name', 'subject', 'chapter').order_by('id')
    questions = list(questions_qs)

    # Read optional metadata (prefer POST, fallback to GET, default to empty string)
    school_name = request.POST.get('school_name') or request.GET.get('school_name', '') or ''
    duration = request.POST.get('duration') or request.GET.get('duration', '') or ''
    total_marks = request.POST.get('total_marks') or request.GET.get('total_marks', '') or ''
    include_omr = bool(request.POST.get('include_omr') or request.GET.get('include_omr'))

    # simple bengali digit converter
    def bengali_digits(value):
        try:
            s = '' if value is None else str(value)
        except Exception:
            return ''
        trans = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')
        return s.translate(trans)

    # prepare questions with precomputed Bengali index strings
    questions_with_index = []
    for idx, q in enumerate(questions, start=1):
        questions_with_index.append({
            'q': q,
            'bn_index': bengali_digits(idx),
            'index': idx,
        })

    context = {
        'questions': questions,
        'questions_with_index': questions_with_index,
        'school_name': school_name,
        'duration': duration,
        'total_marks': total_marks,
        'include_omr': include_omr,
        'duration_bn': bengali_digits(duration),
        'total_marks_bn': bengali_digits(total_marks),
    }
    return render(request, 'core/prepare_paper.html', context)


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
    class_id = request.GET.get('class_id')
    subjects = Subject.objects.filter(class_name_id=class_id).values('id', 'name')
    return JsonResponse(list(subjects), safe=False)

def ajax_load_chapters(request):
    subject_id = request.GET.get('subject_id')
    chapters = Chapter.objects.filter(subject_id=subject_id).values('id', 'name') if subject_id else []
    return JsonResponse(list(chapters), safe=False)


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



