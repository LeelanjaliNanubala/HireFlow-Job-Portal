from django.urls import path

from . import views

app_name = 'applications'

urlpatterns = [
    path('', views.my_applications, name='mine'),
    path('apply/<int:job_id>/', views.apply, name='apply'),
    path('<int:pk>/', views.application_detail, name='detail'),
    path('<int:pk>/withdraw/', views.withdraw, name='withdraw'),
    path('job/<int:job_id>/', views.applicants, name='applicants'),
    path('<int:pk>/review/', views.application_review, name='review'),
    path('<int:pk>/status/', views.update_status, name='update_status'),
]
