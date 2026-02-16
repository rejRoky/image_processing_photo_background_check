"""
Celery configuration for photo_background_check project.

This module configures Celery for asynchronous task processing.
"""

import os

from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'photo_background_check.settings')

app = Celery('photo_background_check')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')


# Configure Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'cleanup-old-photos-daily': {
        'task': 'photo_checker.tasks.cleanup_old_photos_task',
        'schedule': 86400.0,  # Run daily (24 hours)
        'kwargs': {'days': 30},
    },
    'generate-analytics-weekly': {
        'task': 'photo_checker.tasks.generate_analytics_report_task',
        'schedule': 604800.0,  # Run weekly (7 days)
    },
}
