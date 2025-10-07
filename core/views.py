from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import render, redirect


# Create your views here.
def landing_page(request):
    return render(request, template_name='landing_page.html')


# Signup view
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    # 🎯 ফর্মের ফিল্ডগুলোতে CSS ক্লাস এবং placeholder যোগ করা হয়েছে
    form.fields['username'].widget.attrs.update({
        'class': 'form-control',
        'placeholder': 'আপনার পছন্দের ইউজারনেম লিখুন',
        'autofocus': True
    })
    # UserCreationForm দুটি পাসওয়ার্ড ফিল্ড ব্যবহার করে
    form.fields['password1'].widget.attrs.update({
        'class': 'form-control',
        'placeholder': '••••••••••••'
    })
    form.fields['password2'].widget.attrs.update({
        'class': 'form-control',
        'placeholder': '••••••••••••'
    })

    return render(request, 'users/signup.html', {'form': form})


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
    return redirect('landing_page') # Redirect to login page after logout

# Dashboard View - Protected
@login_required
def dashboard_view(request):
    return render(request, 'core/dashboard.html')

@login_required
def question_page(request):
    return render(request, template_name='core/question.html')