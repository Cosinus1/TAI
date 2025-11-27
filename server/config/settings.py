"""
Django settings for urban_mobility_analysis project.
"""

import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'rest_framework',
    'corsheaders',
    'apps.core',
    'apps.mobility',
    'apps.poi',
    'apps.ml',
    'apps.analytics',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('DB_NAME', 'urban_mobility_db'),
        'USER': os.environ.get('DB_USER', 'paulh'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'paulh'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

import warnings
warnings.filterwarnings(
    'ignore',
    message='DateTimeField .* received a naive datetime',
    category=RuntimeWarning
)

import os
import sys

# GDAL configuration for Windows - Auto-detection
if os.name == 'nt':
    # Try common conda and virtual environment paths
    possible_paths = [
        # Current conda environment
        os.path.join(sys.prefix, 'Library', 'bin'),
        # Default conda location
        os.path.join(os.path.expanduser('~'), 'anaconda3', 'Library', 'bin'),
        os.path.join(os.path.expanduser('~'), 'miniconda3', 'Library', 'bin'),
        # Common virtual environment locations
        os.path.join(sys.prefix, 'bin'),
        # System PATH
    ]
    
    # Try to find GDAL DLL
    gdal_found = False
    for path in possible_paths:
        gdal_dll_path = os.path.join(path, 'gdal.dll')
        geos_dll_path = os.path.join(path, 'geos_c.dll')
        
        if os.path.exists(gdal_dll_path):
            GDAL_LIBRARY_PATH = gdal_dll_path
            gdal_found = True
            print(f"Found GDAL at: {gdal_dll_path}")
        
        if os.path.exists(geos_dll_path):
            GEOS_LIBRARY_PATH = geos_dll_path
            print(f"Found GEOS at: {geos_dll_path}")
    
    if not gdal_found:
        print("Warning: GDAL library not found. GIS functionality will be disabled.")