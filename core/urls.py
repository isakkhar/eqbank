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
    path('question_bank/', views.question_bank, name='question_bank'),
    path('question_ready/', views.question_ready, name='question_ready'),

    path('ajax/load-districts/', views.load_districts, name='ajax_load_districts'),
    path('ajax/load-thanas/', views.load_thanas, name='ajax_load_thanas'),
    path('create-paper/', views.create_question_paper_view, name='create_question_paper'),

    # AJAX URLs
    path('ajax/load-subjects/', views.ajax_load_subjects, name='ajax_load_subjects'),
    path('ajax/load-chapters/', views.ajax_load_chapters, name='ajax_load_chapters'),
    # Teacher selection and paper preparation
    path('teacher/select-questions/', views.teacher_question_select, name='teacher_select_questions'),
    path('teacher/prepare-paper/', views.prepare_paper_view, name='prepare_paper'),
    
    # My Papers URLs
    path('my-papers/', views.my_papers_list, name='my_papers_list'),
    path('paper/<int:paper_id>/', views.paper_detail_view, name='paper_detail'),
    path('paper/<int:paper_id>/delete/', views.paper_delete_view, name='paper_delete'),
]
