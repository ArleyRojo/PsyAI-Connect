import os

from .dev import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "psyai_connect_test"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        # Las pruebas no necesitan conexiones persistentes.
        "CONN_MAX_AGE": 0,
    }
}

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}  # noqa: F405
RATELIMIT_ENABLE = False
