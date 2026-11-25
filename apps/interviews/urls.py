from django.urls import path

from . import views

app_name = 'interviews'

urlpatterns = [
    path('mine/', views.my_interviews, name='mine'),
    path('company/', views.recruiter_list, name='recruiter_list'),
    path('schedule/<int:application_id>/', views.schedule, name='schedule'),
    path('<int:pk>/edit/', views.edit, name='edit'),
]
