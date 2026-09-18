from .base import *  # noqa: F401,F403
import os
import sys

DEBUG = False

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

WSGI_APPLICATION = "config.wsgi.application"

# Validate SECRET_KEY in production
_secret = os.getenv("SECRET_KEY", "")
if not _secret or len(_secret) < 50 or _secret.startswith("dev-insecure"):
    print(
        "FATAL: SECRET_KEY is missing, too short, or uses the insecure dev default. "
        "Set a strong SECRET_KEY in your environment.",
        file=sys.stderr,
    )
    sys.exit(1)

# ── Session / CSRF cookies ───────────────────────────────────────────────────
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# ── HSTS ─────────────────────────────────────────────────────────────────────
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ── SSL ──────────────────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ── Additional security headers ──────────────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Compresión de archivos estáticos en producción (uncomment if django-compressor installed)
# COMPRESS_ENABLED = True
# COMPRESS_OFFLINE = True
