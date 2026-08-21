"""
Django settings for smart_inventory project.

Environment-variable-driven configuration following 12-Factor App best practices.
A .env file at the project root is loaded automatically via python-dotenv when
present; production platforms (Render, Railway, Heroku) that inject environment
variables directly are unaffected (load_dotenv() is a no-op when no .env exists).
"""

import os
from pathlib import Path
from decimal import Decimal
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from project root if present (no-op in production when env vars
# are already injected by the platform).
load_dotenv(BASE_DIR / '.env')

# ── Environment & Security ────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-%@l^w$hhm6309k_k%8#8=js(xn_d%egm&%x3z(b7lgo_mvui%t'
)

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

# Safe local-dev default: localhost only. Set ALLOWED_HOSTS in .env or platform
# environment for staging/production.
raw_allowed_hosts = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in raw_allowed_hosts.split(',') if h.strip()]

# ── Application Definition ─────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'catalog',
    'cart',
    'orders',
    'adminpanel',
    'predictions',
]

AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serves static files in prod/dev
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'smart_inventory.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'smart_inventory.wsgi.application'

# ── Database ───────────────────────────────────────────────────────────────────
# Configurable via environment variables (defaults to SQLite3 for dev/testing)
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
    }
}

# ── Password Validation ────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalization ───────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # IST — all template date/time rendering uses this timezone
USE_I18N = True
USE_TZ = True

# ── Static & Media Files ───────────────────────────────────────────────────────
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Email Configuration ────────────────────────────────────────────────────────
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@smartinventory.com')

# Without a timeout, a slow/unresponsive SMTP server (or network/firewall
# interference) can hang the request indefinitely with no feedback to the
# user — the page just looks frozen. This forces send_mail() to fail fast
# with a clear timeout error instead.
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '10'))

# NOTE: SendGrid requires EMAIL_HOST_USER to be the literal string "apikey"
# (not your account email) when EMAIL_HOST is smtp.sendgrid.net.
# EMAIL_HOST_PASSWORD must be a real SendGrid API key (starts with "SG.").

# ── Integrations & Business Constants ──────────────────────────────────────────
GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY', '')
UPI_MERCHANT_ID = os.environ.get('UPI_MERCHANT_ID', '')
DELIVERY_CHARGE = Decimal(os.environ.get('DELIVERY_CHARGE', '40.00'))

# ── Production Security Hardening ──────────────────────────────────────────────
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
