
"""
HireFlow settings.
Secrets and database credentials are read from the .env file (see .env.example).
"""

import os
from pathlib import Path

from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


# ---------------------------------------------------------------- Project paths

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(BASE_DIR / '.env')


# ---------------------------------------------------------------- Environment helpers

def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in (
        '1', 'true', 'yes', 'on'
    )


# ---------------------------------------------------------------- General settings

DEBUG = env_bool('DJANGO_DEBUG', True)

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-development-only-key-change-me'
    else:
        raise ImproperlyConfigured(
            'Set DJANGO_SECRET_KEY in your .env file.'
        )

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv(
        'DJANGO_ALLOWED_HOSTS',
        '127.0.0.1,localhost'
    ).split(',')
    if h.strip()
]


# ---------------------------------------------------------------- Installed apps

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',

    # HireFlow apps
    'apps.common',
    'apps.accounts',
    'apps.candidates',
    'apps.companies',
    'apps.jobs',
    'apps.applications',
    'apps.interviews',
    'apps.notifications',
    'apps.analytics',
]


# ---------------------------------------------------------------- Custom user model

# Must be configured before the first database migration.
AUTH_USER_MODEL = 'accounts.User'


# ---------------------------------------------------------------- Middleware

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ---------------------------------------------------------------- URLs

ROOT_URLCONF = 'config.urls'


# ---------------------------------------------------------------- Templates

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.notifications.context_processors.notifications',
            ],
        },
    },
]


# ---------------------------------------------------------------- WSGI / ASGI

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# ---------------------------------------------------------------- Database

DB_ENGINE = os.getenv('DB_ENGINE', 'mysql').strip().lower()

if DB_ENGINE == 'sqlite':

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

elif DB_ENGINE == 'mysql':

    DB_NAME = os.getenv('DB_NAME', 'hireflow')
    DB_USER = os.getenv('DB_USER', 'hireflow_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = os.getenv('DB_PORT', '3306')

    if not DB_PASSWORD:
        raise ImproperlyConfigured(
            'DB_PASSWORD is missing. Set it in your .env file.'
        )

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,

            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },

            'TEST': {
                'CHARSET': 'utf8mb4',
                'COLLATION': 'utf8mb4_unicode_ci',
            },
        }
    }

else:
    raise ImproperlyConfigured(
        f'Unsupported DB_ENGINE: {DB_ENGINE}. '
        'Use mysql or sqlite.'
    )


# ---------------------------------------------------------------- Authentication

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'
    },
]

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:dashboard'
LOGOUT_REDIRECT_URL = 'home'


# ---------------------------------------------------------------- Internationalisation

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')

USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------- Static files

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ---------------------------------------------------------------- Private media files

# Candidate resumes are stored privately.
# They must only be accessed through permission-checked views.

MEDIA_ROOT = BASE_DIR / 'media_private'
MAX_RESUME_SIZE_MB = 5


# ---------------------------------------------------------------- Default primary key

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------- Email configuration

EMAIL_NOTIFICATIONS_ENABLED = env_bool('EMAIL_ENABLED', False)

DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    'HireFlow <no-reply@example.com>'
)

if EMAIL_NOTIFICATIONS_ENABLED:

    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

    EMAIL_HOST = os.getenv('EMAIL_HOST', '')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

    EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)

else:

    # Emails are printed in the terminal during development.
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# ---------------------------------------------------------------- Messages

MESSAGE_TAGS = {
    message_constants.ERROR: 'danger'
}


# ---------------------------------------------------------------- Django REST Framework

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],

    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],

    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',

    'PAGE_SIZE': 10,

    'EXCEPTION_HANDLER':
        'apps.common.api.api_exception_handler',
}


# ---------------------------------------------------------------- Production security

if not DEBUG:

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True


# ---------------------------------------------------------------- Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },

    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
