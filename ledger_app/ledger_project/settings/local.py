"""
LOCAL / developer-laptop settings.

Inherits everything from base and relaxes constraints that would slow down
day-to-day development (verbose logging, CORS open to Vite dev server, etc.).
"""

from .base import *  # noqa: F401, F403

DEBUG = True

# Accept requests from the Vite dev server and common local ports
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}
