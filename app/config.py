import os
import logging
import json
from datetime import datetime, timedelta


_PLACEHOLDER_KEYS = (
    "your-secret-key-here",
    "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY_USE_secrets.token_urlsafe(50)",
)


class Config:
    def __init__(self):
        self.flask_env = os.getenv("FLASK_ENV", "development").lower()
        self.SECRET_KEY = self._resolve_secret_key()
        self.SESSION_COOKIE_HTTPONLY = True
        self.SESSION_COOKIE_SAMESITE = "Lax"
        self.SESSION_COOKIE_SECURE = self._resolve_session_secure()
        self.SESSION_COOKIE_PATH = "/"
        self.CORS_ORIGINS = self._resolve_cors_origins()
        self.DB_HOST = os.getenv("DB_HOST", "localhost")
        self.DB_PORT = int(os.getenv("DB_PORT", "3306"))
        self.DB_USER = os.getenv("DB_USER", "root")
        self.DB_NAME = os.getenv("DB_NAME", "psyai_connect")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
        self.DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
        self.DB_USE_PURE = os.getenv("DB_USE_PURE", "true").lower() == "true"
        self.MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))
        self.ALLOWED_UPLOAD_EXTENSIONS = self._resolve_allowed_extensions()
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "text")
        self.RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
        self.REGISTER_RATE_LIMIT = self._resolve_rate_limit("REGISTER_RATE_LIMIT", "5 per minute", "20 per minute")
        self.LOGIN_RATE_LIMIT = self._resolve_rate_limit("LOGIN_RATE_LIMIT", "10 per minute", "60 per minute")
        self.PASSWORD_RECOVERY_RATE_LIMIT = self._resolve_rate_limit("PASSWORD_RECOVERY_RATE_LIMIT", "3 per minute", "10 per minute")
        self.PERMANENT_SESSION_LIFETIME = timedelta(days=7)
        self.WTF_CSRF_ENABLED = os.getenv("WTF_CSRF_ENABLED", "true").lower() == "true"
        self.WTF_CSRF_TIME_LIMIT = int(os.getenv("WTF_CSRF_TIME_LIMIT", "3600"))
        self.WTF_CSRF_SSL_STRICT = os.getenv("WTF_CSRF_SSL_STRICT", "false").lower() == "true"
        self.WTF_CSRF_CHECK_DEFAULT = os.getenv("WTF_CSRF_CHECK_DEFAULT", "true").lower() == "true"
        self.WTF_CSRF_HEADERS = os.getenv("WTF_CSRF_HEADERS", "X-CSRFToken,X-CSRF-Token").split(",")
        self.WOMPI_ENV = os.getenv("WOMPI_ENV", "test").lower()
        self.WOMPI_PUBLIC_KEY = os.getenv("WOMPI_PUBLIC_KEY", "")
        self.WOMPI_PRIVATE_KEY = os.getenv("WOMPI_PRIVATE_KEY", "")
        self.WOMPI_INTEGRITY_SECRET = os.getenv("WOMPI_INTEGRITY_SECRET", "")
        self.WOMPI_EVENTS_SECRET = os.getenv("WOMPI_EVENTS_SECRET", "")
        self.WOMPI_API_BASE = "https://production.wompi.co/v1" if self.WOMPI_ENV == "prod" else "https://sandbox.wompi.co/v1"
        self.WOMPI_CHECKOUT_URL = "https://checkout.wompi.co/p/"

    def _resolve_secret_key(self):
        key = os.getenv("SECRET_KEY")
        if not key or key in _PLACEHOLDER_KEYS:
            if self.flask_env == "production":
                raise ValueError(
                    "SECRET_KEY debe estar definida en producción. "
                    "Ejecuta: python -c \"import secrets; print(secrets.token_urlsafe(50))\""
                )
            import secrets
            key = secrets.token_urlsafe(50)
            logging.warning(
                "SECRET_KEY no configurada. Se generó una clave temporal. "
                "Defina SECRET_KEY en .env para evitar que las sesiones se reinicien."
            )
        return key

    def _resolve_session_secure(self):
        env_val = os.getenv("SESSION_COOKIE_SECURE", "false").lower()
        return env_val == "true" or self.flask_env == "production"

    def _resolve_cors_origins(self):
        return os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5000,http://127.0.0.1:5000,https://psyai-connect.com"
        ).split(",")

    def _resolve_allowed_extensions(self):
        return set(
            os.getenv("ALLOWED_UPLOAD_EXTENSIONS", "jpg,jpeg,png,pdf,gif,webp,doc,docx").split(",")
        )

    def _resolve_rate_limit(self, env_var, production_val, development_val):
        return os.getenv(env_var, production_val if self.flask_env == "production" else development_val)

    def setup_logging(self, app):
        werkzeug_logger = logging.getLogger("werkzeug")
        werkzeug_logger.handlers.clear()
        werkzeug_logger.setLevel(logging.INFO if os.getenv("SHOW_WERKZEUG_LOGS", "0") == "1" else logging.WARNING)
        werkzeug_logger.propagate = True

        werkzeug_serving_logger = logging.getLogger("werkzeug.serving")
        werkzeug_serving_logger.handlers.clear()
        werkzeug_serving_logger.setLevel(werkzeug_logger.level)
        werkzeug_serving_logger.propagate = True

        logging.getLogger("flask-limiter").setLevel(logging.WARNING)
        return werkzeug_logger


config = Config()


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "ip_address"):
            log_data["ip_address"] = record.ip_address
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    def format(self, record):
        return f"{datetime.utcnow().isoformat()}Z | {record.levelname:8} | {record.name:20} | {record.getMessage()}"
