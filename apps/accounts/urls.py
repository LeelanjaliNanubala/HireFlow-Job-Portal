from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.HireFlowLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),  # logout must be a POST request
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('register/candidate/', views.register_candidate, name='register_candidate'),
    path('register/recruiter/', views.register_recruiter, name='register_recruiter'),
    path('password-reset/', views.HireFlowPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.HireFlowPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.HireFlowPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('reset/done/', views.HireFlowPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
