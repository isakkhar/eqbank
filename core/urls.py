from django.urls import path

from . import views
from .views import landing_page

urlpatterns = [
    path('', landing_page, name='landing_page'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('question/', views.question_page, name='question'),

]