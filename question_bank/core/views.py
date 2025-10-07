from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, redirect

from core.forms import SignUpForm, BANGLADESH_DIVISIONS_DISTRICTS_THANAS
from .models import Profile


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
    return render(request, template_name='core/question.html')


@login_required
def question_bank(request):
    return render(request, template_name='core/question_bank.html')
