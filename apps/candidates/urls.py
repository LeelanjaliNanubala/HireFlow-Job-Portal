from django.urls import path

from . import views

app_name = 'candidates'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_edit, name='profile'),
    path('education/', views.education, name='education'),
    path('education/<int:pk>/delete/', views.education_delete, name='education_delete'),
    path('experience/', views.experience, name='experience'),
    path('experience/<int:pk>/delete/', views.experience_delete, name='experience_delete'),
    path('skills/', views.skills, name='skills'),
    path('skills/<int:pk>/remove/', views.skill_remove, name='skill_remove'),
    path('resumes/', views.resumes, name='resumes'),
    path('resumes/<int:pk>/delete/', views.resume_delete, name='resume_delete'),
    path('resumes/<int:pk>/default/', views.resume_make_default, name='resume_default'),
    path('resumes/<int:pk>/download/', views.resume_download, name='resume_download'),
    path('saved-jobs/', views.saved_jobs, name='saved_jobs'),
    path('saved-jobs/toggle/<int:job_id>/', views.toggle_saved, name='toggle_saved'),
]
