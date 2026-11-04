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

# ── WhiteNoise: servir estáticos en producción (gzip/brotli + caché inmutable) ──
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
] + [m for m in MIDDLEWARE if m not in (
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
)]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Caché inmutable (1 año) y compresión automática gzip/brotli en WhiteNoise
WHITENOISE_MAX_AGE = 31536000
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = False

# ── Caché en producción (LocMemCache, un solo worker en Render plan gratis) ──
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "psyai-connect-cache",
        "TIMEOUT": 120,
        "OPTIONS": {
            "MAX_ENTRIES": 2000,
        },
    }
}

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
