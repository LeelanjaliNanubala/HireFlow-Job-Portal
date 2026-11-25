"""All REST API routes (mounted under /api/)."""
from django.urls import path

from apps.accounts import api as accounts_api
from apps.applications import api as applications_api
from apps.interviews import api as interviews_api
from apps.jobs import api as jobs_api
from apps.notifications import api as notifications_api

urlpatterns = [
    # Authentication
    path('auth/register/', accounts_api.RegisterAPIView.as_view(), name='api-register'),
    path('auth/login/', accounts_api.LoginAPIView.as_view(), name='api-login'),
    path('auth/logout/', accounts_api.LogoutAPIView.as_view(), name='api-logout'),
    # Jobs
    path('jobs/', jobs_api.JobListCreateAPIView.as_view(), name='api-jobs'),
    path('jobs/<int:pk>/', jobs_api.JobDetailAPIView.as_view(), name='api-job-detail'),
    # Applications
    path('applications/', applications_api.ApplicationCreateAPIView.as_view(), name='api-apply'),
    path('me/applications/', applications_api.MyApplicationsAPIView.as_view(), name='api-my-applications'),
    path('recruiter/jobs/<int:pk>/applications/', applications_api.JobApplicationsAPIView.as_view(),
         name='api-job-applications'),
    path('applications/<int:pk>/status/', applications_api.ApplicationStatusAPIView.as_view(),
         name='api-application-status'),
    # Interviews
    path('applications/<int:pk>/interviews/', interviews_api.InterviewCreateAPIView.as_view(),
         name='api-interview-create'),
    # Notifications
    path('me/notifications/', notifications_api.MyNotificationsAPIView.as_view(), name='api-my-notifications'),
]
