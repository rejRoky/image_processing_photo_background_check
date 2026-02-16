"""
Staging settings for photo_background_check project.

These settings mirror production but with some relaxed constraints for testing.
"""

from .production import *

# =============================================================================
# CORE OVERRIDES
# =============================================================================

# Allow additional hosts for staging
ALLOWED_HOSTS = get_env_list(
    'DJANGO_ALLOWED_HOSTS',
    default='staging.yourdomain.com,*.staging.yourdomain.com'
)


# =============================================================================
# DEBUGGING (Limited debugging in staging)
# =============================================================================

DEBUG = get_env_bool('DJANGO_DEBUG', default=False)


# =============================================================================
# LOGGING (More verbose than production)
# =============================================================================

LOGGING['loggers']['photo_checker']['level'] = 'DEBUG'


# =============================================================================
# SENTRY (Staging environment)
# =============================================================================

if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment='staging',
        traces_sample_rate=0.5,  # Higher sampling for staging
    )


# =============================================================================
# THROTTLING (Relaxed for testing)
# =============================================================================

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '500/hour',
    'user': '5000/hour',
}
