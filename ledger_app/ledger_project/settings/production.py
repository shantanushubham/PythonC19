"""
Production settings (also used for STG).

Inherits from base and hardens security.  All sensitive values MUST come
from environment variables — never hard-code them here.
"""

from decouple import Csv, config

from .base import *  # noqa: F401, F403

DEBUG = False

# CORS: supply a comma-separated list in the env, e.g.
#   CORS_ALLOWED_ORIGINS=https://app.example.com,https://www.example.com
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", cast=Csv())

# Redirect all HTTP → HTTPS.
# Set SECURE_SSL_REDIRECT=False when running behind a terminating proxy
# (e.g. an AWS ALB / nginx) that already handles TLS, or during initial
# Docker bring-up without a TLS terminator in front.
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS — tell browsers to enforce HTTPS for 1 year
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}
