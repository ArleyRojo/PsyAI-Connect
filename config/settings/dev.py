from .base import *  # noqa: F401,F403

DEBUG = True

WSGI_APPLICATION = "config.wsgi.application"

ALLOWED_HOSTS = ["*"]

CORS_ALLOW_ALL_ORIGINS = True
