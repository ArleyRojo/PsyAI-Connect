import os
import logging

logging.getLogger('werkzeug').setLevel(logging.ERROR)

from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException

from app.config import Config, setup_logging
from app.database.connection import init_pool

from app.routes.admin_routes import admin_bp
from app.routes.appointment_routes import appointment_bp
from app.routes.auth_routes import auth_bp
from app.routes.page_routes import pages_bp
from app.routes.patient_routes import patient_bp
from app.routes.professional_routes import professional_bp
from app.routes.theme_routes import theme_bp
from app.services.telemetry_service import track_request, track_latency


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder=None,
    )
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    setup_logging(app)
    init_pool(app)

    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["5000 per day", "2000 per hour"],
        storage_uri=Config.RATELIMIT_STORAGE_URI,
    )

    def get_limiter():
        limiters = app.extensions.get("limiter", set())
        return next(iter(limiters)) if limiters else None

    app.get_limiter = get_limiter

    CORS(app, supports_credentials=True, origins=Config.CORS_ORIGINS)

    app.register_blueprint(theme_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(professional_bp)
    app.register_blueprint(appointment_bp)
    app.register_blueprint(pages_bp)

    @app.route("/healthz")
    def healthz():
        db_connected = False
        try:
            from app.utils.db import db_cursor
            with db_cursor() as (_, cursor):
                cursor.execute("SELECT 1")
                db_connected = cursor.fetchone() is not None
        except Exception as exc:
            app.logger.warning("Healthcheck DB failed: %s", exc)
        return {
            "status": "healthy" if db_connected else "degraded",
            "version": "1.0.0",
            "db": "Conectada" if db_connected else "Sin conexion",
            "db_connected": db_connected,
            "environment": app.config.get("ENV", os.getenv("FLASK_ENV", "development")),
        }, 200 if db_connected else 503

    @app.before_request
    def telemetry_hook():
        import time as _time
        from flask import request, g
        g._telemetry_start = _time.time()
        # Ignore static files
        if request.path.startswith("/css/") or request.path.startswith("/js/") or request.path.startswith("/img/"):
            return
        track_request(get_remote_address(), request.path)

    @app.after_request
    def telemetry_latency(response):
        import time as _time
        from flask import g
        start = getattr(g, '_telemetry_start', None)
        if start:
            duration_ms = (_time.time() - start) * 1000
            track_latency(duration_ms)
        return response

    @app.errorhandler(404)
    def handle_404(error):
        app.logger.warning("Error 404: %s", error)
        return jsonify({"success": False, "message": "Recurso no encontrado"}), 404

    @app.errorhandler(500)
    def handle_500(error):
        app.logger.exception("Error 500: %s", error)
        return jsonify({"success": False, "message": "Error interno del servidor"}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        if isinstance(error, HTTPException):
            app.logger.warning("Error HTTP %s: %s", error.code, error)
            return jsonify({"success": False, "message": error.description}), error.code
        app.logger.exception("Error no controlado: %s", error)
        return jsonify({"success": False, "message": "Error interno del servidor"}), 500

    return app
