import os
import logging
import json
import secrets
from datetime import datetime, timedelta


class Config:
    # Determinar entorno temprano para validaciones
    _flask_env = os.getenv("FLASK_ENV", "development").lower()

    # SECRET_KEY: obligatoria en producción, en desarrollo se genera si falta
    _secret_key = os.getenv("SECRET_KEY")
    _placeholders = (
        "your-secret-key-here",
        "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY_USE_secrets.token_urlsafe(50)",
    )
    if not _secret_key or _secret_key in _placeholders:
        if _flask_env == "production":
            raise ValueError(
                "SECRET_KEY debe estar definida en producción. "
                "Ejecuta: python -c \"import secrets; print(secrets.token_urlsafe(50))\""
            )
        import secrets

        _secret_key = secrets.token_urlsafe(50)
        logging.warning(
            "SECRET_KEY no configurada. Se generó una clave temporal. "
            "Defina SECRET_KEY en .env para evitar que las sesiones se reinicien."
        )
    SECRET_KEY = _secret_key

    FLASK_ENV = _flask_env

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
        or FLASK_ENV == "production"
    )
    SESSION_COOKIE_PATH = "/"

    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000,https://psyai-connect.com"
    ).split(",")

    # Database con defaults sensatos para desarrollo local
    # DB_POOL_SIZE: Tamaño del pool de conexiones MySQL.
    #   Default 10. Con SSE activo cada cliente consume una conexión,
    #   por lo que valores <8 generan una advertencia en el log.
    # DB_USE_PURE: Usar driver Python puro (true) o C nativo (false).
    #   En producción con mysql-connector-python[c-ext] instalado,
    #   usar DB_USE_PURE=false para 3-5x mejor rendimiento.
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_NAME = os.getenv("DB_NAME", "psyai_connect")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_USE_PURE = os.getenv("DB_USE_PURE", "true").lower() == "true"

    # Upload validation
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))
    ALLOWED_UPLOAD_EXTENSIONS = set(
<<<<<<< HEAD
        os.getenv("ALLOWED_UPLOAD_EXTENSIONS", "jpg,jpeg,png,pdf,gif,webp").split(",")
=======
        os.getenv("ALLOWED_UPLOAD_EXTENSIONS", "jpg,jpeg,png,pdf,gif,webp,doc,docx").split(",")
>>>>>>> 629d7c0 (avances)
    )

    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "text")

    # ADVERTENCIA: memory:// no escala con múltiples workers ni persiste entre reinicios.
    # En producción usar: redis://localhost:6379/0
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    _is_production = FLASK_ENV == "production"
    REGISTER_RATE_LIMIT = os.getenv(
        "REGISTER_RATE_LIMIT",
        "5 per minute" if _is_production else "20 per minute",
    )
    LOGIN_RATE_LIMIT = os.getenv(
        "LOGIN_RATE_LIMIT",
        "10 per minute" if _is_production else "60 per minute",
    )
    PASSWORD_RECOVERY_RATE_LIMIT = os.getenv(
        "PASSWORD_RECOVERY_RATE_LIMIT",
        "3 per minute" if _is_production else "10 per minute",
    )

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # CSRF protection
    WTF_CSRF_ENABLED = os.getenv("WTF_CSRF_ENABLED", "true").lower() == "true"
    WTF_CSRF_TIME_LIMIT = int(os.getenv("WTF_CSRF_TIME_LIMIT", "3600"))
    WTF_CSRF_SSL_STRICT = os.getenv("WTF_CSRF_SSL_STRICT", "false").lower() == "true"
    WTF_CSRF_CHECK_DEFAULT = os.getenv("WTF_CSRF_CHECK_DEFAULT", "true").lower() == "true"
    WTF_CSRF_HEADERS = os.getenv("WTF_CSRF_HEADERS", "X-CSRFToken,X-CSRF-Token").split(",")


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


def setup_logging(app):
    # Siempre mostrar werkzeug logs en desarrollo
    werkzeug_logger = logging.getLogger('werkzeug')
    
    # En desarrollo, usar DEBUG level
    if os.getenv("FLASK_ENV", "development").lower() == "development":
        werkzeug_logger.setLevel(logging.DEBUG)
    else:
        werkzeug_logger.setLevel(logging.INFO)
    
    # Asegurar que tiene un handler para mostrar en terminal
    if not werkzeug_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
        handler.setFormatter(formatter)
        werkzeug_logger.addHandler(handler)
    
    # Forzar propagación
    werkzeug_logger.propagate = True
    
    # Configurar otros loggers
    logging.getLogger('flask-limiter').setLevel(logging.WARNING)
    
    return werkzeug_logger


def setup_logging(app):
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
