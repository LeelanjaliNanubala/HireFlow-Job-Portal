from django.urls import path

from . import views

app_name = 'analytics'

urlpatterns = [
    path('recruiter/', views.recruiter_dashboard, name='recruiter_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/<int:pk>/toggle/', views.admin_user_toggle, name='admin_user_toggle'),
    path('admin/companies/', views.admin_companies, name='admin_companies'),
    path('admin/companies/<int:pk>/review/', views.admin_company_review, name='admin_company_review'),
    path('admin/jobs/', views.admin_jobs, name='admin_jobs'),
    path('admin/jobs/<int:pk>/moderate/', views.admin_job_moderate, name='admin_job_moderate'),
    path('admin/applications/', views.admin_applications, name='admin_applications'),
    path('admin/audit/', views.admin_audit, name='admin_audit'),
]
