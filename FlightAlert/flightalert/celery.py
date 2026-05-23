import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flightalert.settings")

app = Celery("flightalert")

# Pull CELERY_* keys from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all INSTALLED_APPS
app.autodiscover_tasks()
