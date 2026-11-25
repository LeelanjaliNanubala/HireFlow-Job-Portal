from django.urls import path

from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.job_list, name='list'),
    path('manage/', views.manage_list, name='manage'),
    path('manage/new/', views.job_create, name='create'),
    path('manage/<int:pk>/edit/', views.job_edit, name='edit'),
    path('manage/<int:pk>/status/', views.job_status, name='status'),
    path('<int:pk>/', views.job_detail, name='detail'),
]
