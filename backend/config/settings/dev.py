"""
Development settings — do NOT use in production.
"""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Clean, readable console logs — no SQL spam
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "clean": {
            "format": "[{asctime}] {levelname:<8} {name} — {message}",
            "datefmt": "%H:%M:%S",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "clean",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        # Our app logs — show INFO and above (login, transfer, alert, OTP events)
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Django request log — shows  GET /api/... 200  lines only
        "django.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Silence SQL queries entirely
        "django.db.backends": {
            "handlers": [],
            "level": "CRITICAL",
            "propagate": False,
        },
    },
}
