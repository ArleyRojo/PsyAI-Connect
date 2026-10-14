import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key-change-me")

DEBUG = False

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "corsheaders",
    "rest_framework",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    "apps.authentication.apps.AuthenticationConfig",
    "apps.patients.apps.PatientsConfig",
    "apps.professionals.apps.ProfessionalsConfig",
    "apps.scheduling.apps.SchedulingConfig",
    "apps.chatbot.apps.ChatbotConfig",
    "apps.documents.apps.DocumentsConfig",
    "apps.billing.apps.BillingConfig",
    "apps.admin_panel.apps.AdminPanelConfig",
    "apps.core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # "whitenoise.middleware.WhiteNoiseMiddleware",  # uncomment if installed
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.core.middleware.security_headers.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "psyai_connect"),
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", "root"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
        "CONN_MAX_AGE": 60,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"  # uncomment if installed

# WHITENOISE_USE_FINDERS = True
# WHITENOISE_MANIFEST_STRICT = False
# WHITENOISE_MAX_AGE = 31536000

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Security defaults (overridden in prod.py) ────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.authentication.authentication.CsrfEnforcedSessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "120/minute",
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

AUTH_USER_MODEL = "authentication.Register"

CORS_ALLOW_CREDENTIALS = True
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5000,http://127.0.0.1:5000,https://psyai-connect.com",
).split(",")

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in CORS_ORIGINS if origin.strip()
]

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_AGE = 604800
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# CSRF
CSRF_COOKIE_HTTPONLY = True  # En producción True; en dev se puede poner False en dev.py
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000,https://psyai-connect.com",
    ).split(",") if origin.strip()
]

# Content Security Policy
CSP_ENABLED = True

ALLOWED_UPLOAD_EXTENSIONS: set[str] = set(
    os.getenv("ALLOWED_UPLOAD_EXTENSIONS", "jpg,jpeg,png,pdf,gif,webp,doc,docx").split(",")
)
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))

REGISTER_RATE_LIMIT = os.getenv("REGISTER_RATE_LIMIT", "20 per minute")
LOGIN_RATE_LIMIT = os.getenv("LOGIN_RATE_LIMIT", "60 per minute")
PASSWORD_RECOVERY_RATE_LIMIT = os.getenv("PASSWORD_RECOVERY_RATE_LIMIT", "10 per minute")

WOMPI_ENV = os.getenv("WOMPI_ENV", "test").lower()
WOMPI_PUBLIC_KEY = os.getenv("WOMPI_PUBLIC_KEY", "")
WOMPI_PRIVATE_KEY = os.getenv("WOMPI_PRIVATE_KEY", "")
WOMPI_INTEGRITY_SECRET = os.getenv("WOMPI_INTEGRITY_SECRET", "")
WOMPI_EVENTS_SECRET = os.getenv("WOMPI_EVENTS_SECRET", "")
WOMPI_API_BASE = (
    "https://production.wompi.co/v1"
    if WOMPI_ENV == "prod"
    else "https://sandbox.wompi.co/v1"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "low")

SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")

# Django email (SMTP)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")

# WhatsApp / Twilio
def _parse_bool(val: str) -> bool:
    return val.strip().lower() in ("1", "true", "yes", "on")

WHATSAPP_ENABLED = _parse_bool(os.getenv("WHATSAPP_ENABLED", "False"))
TWILIO_SID = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")   # ej. whatsapp:+14155238886
TWILIO_WEBHOOK_URL = os.getenv("TWILIO_WEBHOOK_URL", "")
TWILIO_STATUS_CALLBACK_URL = os.getenv("TWILIO_STATUS_CALLBACK_URL", "")
# Plantillas (Content SIDs) – configurar en producción
TWILIO_TPL_RECORDATORIO = os.getenv("TWILIO_TPL_RECORDATORIO", "")
TWILIO_TPL_CONFIRMACION = os.getenv("TWILIO_TPL_CONFIRMACION", "")
TWILIO_TPL_CANCELACION = os.getenv("TWILIO_TPL_CANCELACION", "")
TWILIO_TPL_MENSAJE_PRO = os.getenv("TWILIO_TPL_MENSAJE_PRO", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "PsyAI Connect <noreply@psyaiconnect.com>")

# En desarrollo sin credenciales SMTP, imprime el correo en consola
if DEBUG and not EMAIL_HOST_USER:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Logging por consola estilo Django (validado para dev, prod y test)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        },
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "stream": sys.stdout,
        },
        "django.server": {
            "class": "logging.StreamHandler",
            "formatter": "django.server",
            "stream": sys.stdout,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Cache framework
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "psyai-connect-cache",
        "TIMEOUT": 30,
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        },
    }
}

# WhiteNoise static file serving (optional — remove if not installed)
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
# WHITENOISE_USE_FINDERS = True
# WHITENOISE_MANIFEST_STRICT = False
# WHITENOISE_MAX_AGE = 31536000

# ── Django Sites ──────────────────────────────────────────────────────────────
SITE_ID = 1

# ── django-allauth ────────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# URL de redirecionamiento tras login/logout exitoso
LOGIN_REDIRECT_URL = "/api/social-redirect"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "/login.html"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_ADAPTER = "allauth.account.adapter.DefaultAccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.authentication.adapters.SocialAccountAdapter"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

# Providers de redes sociales
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "CALLBACK_URL": "http://localhost:8000/accounts/google/login/callback/",
    },

}

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_BASE_URL = "http://localhost:8000"
SOCIALACCOUNT_LOGIN_REDIRECT_URL = "/"
