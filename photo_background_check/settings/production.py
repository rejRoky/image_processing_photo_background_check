"""
Production settings for photo_background_check project.

These settings are optimized for security and performance in production.
Ensure all environment variables are properly configured before deployment.
"""

import os
from .base import *

# =============================================================================
# CORE SETTINGS
# =============================================================================

DEBUG = False

SECRET_KEY = get_env_variable('DJANGO_SECRET_KEY', required=True)

ALLOWED_HOSTS = get_env_list('DJANGO_ALLOWED_HOSTS', required=False)
if not ALLOWED_HOSTS:
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set in production")


# =============================================================================
# DATABASE (PostgreSQL recommended for production)
# =============================================================================

DATABASE_URL = get_env_variable('DATABASE_URL')

if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    raise ValueError("DATABASE_URL must be set in production")


# =============================================================================
# CACHING (Redis recommended for production)
# =============================================================================

REDIS_URL = get_env_variable('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'photo_bg_check',
        'TIMEOUT': 300,
    }
}

# Use cache for sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'


# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# HTTPS/SSL
SECURE_SSL_REDIRECT = get_env_bool('SECURE_SSL_REDIRECT', default=True)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS
SECURE_HSTS_SECONDS = get_env_int('SECURE_HSTS_SECONDS', default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies
SESSION_COOKIE_SECURE = get_env_bool('SESSION_COOKIE_SECURE', default=True)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = get_env_bool('CSRF_COOKIE_SECURE', default=True)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Referrer Policy
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'


# =============================================================================
# STATIC FILES
# =============================================================================

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# =============================================================================
# LOGGING (Structured logging for production)
# =============================================================================

LOGGING['handlers']['console']['formatter'] = 'json'
LOGGING['loggers']['django']['handlers'] = ['console']
LOGGING['loggers']['photo_checker']['handlers'] = ['console']

# Remove file handlers in production (use centralized logging)
if 'file' in LOGGING['handlers']:
    del LOGGING['handlers']['file']
if 'error_file' in LOGGING['handlers']:
    del LOGGING['handlers']['error_file']


# =============================================================================
# SENTRY (Error Tracking - Optional)
# =============================================================================

SENTRY_DSN = get_env_variable('SENTRY_DSN')

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,
        environment='production',
    )


# =============================================================================
# EMAIL (Production SMTP)
# =============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = get_env_variable('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = get_env_int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = get_env_variable('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = get_env_variable('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = get_env_bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = get_env_variable('DEFAULT_FROM_EMAIL', default='noreply@example.com')


# =============================================================================
# REST FRAMEWORK (Production settings)
# =============================================================================

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
]


# =============================================================================
# HEALTH CHECK
# =============================================================================

HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # percent
    'MEMORY_MIN': 100,     # MB
}
