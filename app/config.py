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
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_NAME = os.getenv("DB_NAME", "psyai_connect")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "root")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "werkzeug")

    # ADVERTENCIA: memory:// no escala con múltiples workers ni persiste entre reinicios.
    # En producción usar: redis://localhost:6379/0
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)


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
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper())
    log_format = app.config.get("LOG_FORMAT", "werkzeug")
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    
    if log_format == "werkzeug":
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(logging.INFO)
        if not any(isinstance(h, logging.StreamHandler) for h in werkzeug_logger.handlers):
            werkzeug_logger.addHandler(logging.StreamHandler())
        logging.getLogger('flask-limiter').setLevel(logging.WARNING)
        return None
    
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    app.logger.setLevel(log_level)
    app.logger.handlers = []
    app.logger.addHandler(console_handler)
    
    return app.logger