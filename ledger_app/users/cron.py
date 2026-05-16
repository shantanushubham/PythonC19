from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "daily-report": {
        "task": "users.views.send_daily_report",
        "schedule": 5.0 # in seconds
    }
}
