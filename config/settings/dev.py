from .base import *  # noqa: F401,F403

DEBUG = True

WSGI_APPLICATION = "config.wsgi.application"

ALLOWED_HOSTS = ["*"]

CORS_ALLOW_ALL_ORIGINS = True

# Console email backend for development (prints emails to terminal)
if not EMAIL_HOST_USER:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
