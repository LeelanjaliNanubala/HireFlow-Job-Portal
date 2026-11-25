"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path

from apps.jobs.views import home

urlpatterns = [
    # Django's built-in admin panel (technical data editing).
    path('django-admin/', admin.site.urls),
    # Public home page.
    path('', home, name='home'),
    path('accounts/', include('apps.accounts.urls')),
    path('candidate/', include('apps.candidates.urls')),
    path('companies/', include('apps.companies.urls')),
    path('jobs/', include('apps.jobs.urls')),
    path('applications/', include('apps.applications.urls')),
    path('interviews/', include('apps.interviews.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('dashboard/', include('apps.analytics.urls')),
    path('api/', include('config.api_urls')),
]
