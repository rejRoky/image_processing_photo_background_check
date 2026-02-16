"""
Development settings for photo_background_check project.

These settings are meant for local development only.
Never use these settings in production!
"""

from .base import *

# =============================================================================
# CORE SETTINGS
# =============================================================================

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '*']

SECRET_KEY = 'django-insecure-dev-only-key-change-in-production'


# =============================================================================
# DATABASE
# =============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# =============================================================================
# CACHING (Use local memory for development)
# =============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}


# =============================================================================
# REST FRAMEWORK (Relaxed throttling for development)
# =============================================================================

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '1000/hour',
    'user': '10000/hour',
}

# Add browsable API for development
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]


# =============================================================================
# CORS (Allow all origins in development)
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = True


# =============================================================================
# EMAIL (Use console backend for development)
# =============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# =============================================================================
# LOGGING (More verbose in development)
# =============================================================================

LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['loggers']['photo_checker']['level'] = 'DEBUG'


# =============================================================================
# DEBUG TOOLBAR (Optional)
# =============================================================================

try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass


# =============================================================================
# CELERY (Use synchronous execution in development)
# =============================================================================

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
