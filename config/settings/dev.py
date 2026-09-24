from .base import *  # noqa: F401,F403

DEBUG = True

WSGI_APPLICATION = "config.wsgi.application"

ALLOWED_HOSTS = ["*"]

CORS_ALLOW_ALL_ORIGINS = True

# En desarrollo permitir leer cookie CSRF desde JS
CSRF_COOKIE_HTTPONLY = False

# Console email backend for development (prints emails to terminal)
if not EMAIL_HOST_USER:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ── DB local ─────────────────────────────────────────────────────────────────
# Por defecto SQLite en archivo para que `runserver` funcione sin Docker/MySQL.
# Docker Compose inyecta DB_HOST=db + credenciales, pero fuera de Docker ese
# host no resuelve ("Unknown server host 'db'"). Para usar MySQL local:
#   USE_MYSQL=1 python manage.py runserver
# (con DB_HOST localhost y un MySQL corriendo con las credenciales del .env).
if os.getenv("USE_MYSQL", "").strip() not in ("1", "true", "yes"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
