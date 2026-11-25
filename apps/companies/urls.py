from django.urls import path

from . import views

app_name = 'companies'

urlpatterns = [
    path('my-company/', views.company_edit, name='edit'),
    path('<int:pk>/', views.company_detail, name='detail'),
]
