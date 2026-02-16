"""
Settings module for photo_background_check project.

This module automatically selects the appropriate settings based on
the DJANGO_ENVIRONMENT environment variable.
"""

import os

environment = os.environ.get('DJANGO_ENVIRONMENT', 'development')

if environment == 'production':
    from .production import *
elif environment == 'staging':
    from .staging import *
else:
    from .development import *
