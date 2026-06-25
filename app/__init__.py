import datetime
import os
import re
import time
from urllib.parse import urlparse

from flask import Flask, current_app, g, jsonify, request, session
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
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


class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, datetime.time):
            return obj.isoformat()
        return super().default(obj)


TABLAS_CRITICAS = [
    "Register", "PerfilPaciente", "PerfilProfesional", "AuditoriaAccesos",
    "Login", "Disponibilidad", "Citas", "ConversacionesChatbot",
    "EvolucionPaciente", "PacientesProfesional", "Notificaciones",
    "ChatbotConfig", "EncuestaChatbot", "MensajesChat", "RecoveryTokens",
    "intentos_fallidos",
]


def verificar_tablas(app):
    from app.utils.db import db_cursor
    with app.app_context():
        try:
            with db_cursor() as (_, cursor):
                cursor.execute("SHOW TABLES")
                existentes = {row[0] for row in cursor.fetchall()}
                faltantes = [t for t in TABLAS_CRITICAS if t not in existentes]
                if faltantes:
                    app.logger.critical(
                        "TABLAS FALTANTES EN BD: %s — Corre el SQL de migración antes de iniciar.",
                        ", ".join(faltantes),
                    )
                else:
                    app.logger.info("BD verificada: todas las tablas críticas existen.")
        except Exception as e:
            app.logger.critical("No se pudo verificar la BD al arrancar: %s", e)


API_PATTERN = re.compile(
    r"""(?:
        fetch\(\s*[`'"]([^`'"]*(?:/api/|/healthz)[^`'"]*)[`'"] |
        new\s+EventSource\(\s*[`'"]([^`'"]*(?:/api/|/healthz)[^`'"]*)[`'"] |
        data-[\w-]*endpoint=["']([^"']*(?:/api/|/healthz)[^"']*)["']
    )""",
    re.IGNORECASE | re.VERBOSE,
)

SCRIPT_PATTERN = re.compile(r"""<script[^>]+src=["']([^"']+\.js(?:\?[^"']*)?)["']""", re.IGNORECASE)
STYLESHEET_PATTERN = re.compile(
    r"""<link[^>]+rel=["'][^"']*stylesheet[^"']*["'][^>]+href=["']([^"']+)["']|"""
    r"""<link[^>]+href=["']([^"']+)["'][^>]+rel=["'][^"']*stylesheet[^"']*["']""",
    re.IGNORECASE,
)


class RequestLoggingMiddleware:
    """WSGI middleware that logs REST API requests in the terminal."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "UNKNOWN")
        path = environ.get("PATH_INFO", "/")
        start_time = time.time()
        status_holder = {"status": "000"}

        def logging_start_response(status, headers, exc_info=None):
            status_holder["status"] = status.split(" ", 1)[0]
            return start_response(status, headers, exc_info)

        try:
            return self.app(environ, logging_start_response)
        finally:
            if path.startswith("/api/") or path == "/healthz":
                duration_ms = (time.time() - start_time) * 1000
                label = "[API ACCION]" if method in {"POST", "PUT", "PATCH", "DELETE"} else "[API REST]"
                print(
                    f"{label} {method} - {status_holder['status']:>3} {duration_ms:8.1f} ms  {path}",
                    flush=True,
                )


def _clean_api_reference(raw_url):
    if not raw_url:
        return None
    cleaned = raw_url.strip()
    cleaned = cleaned.replace("${API}", "").replace("${window.API_BASE || ''}", "")
    parsed = urlparse(cleaned)
    path = parsed.path or cleaned
    if "/api/" not in path and path != "/healthz":
        return None
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{path}{query}"


def _extract_api_references(source):
    apis = set()
    for match in API_PATTERN.finditer(source or ""):
        for group in match.groups():
            api = _clean_api_reference(group)
            if api:
                apis.add(api)
    return apis


def _clean_resource_reference(raw_url):
    if not raw_url:
        return None
    cleaned = raw_url.strip()
    if not cleaned or cleaned.startswith(("data:", "javascript:")):
        return None
    return cleaned


def _extract_stylesheets(html):
    stylesheets = set()
    for match in STYLESHEET_PATTERN.finditer(html or ""):
        for group in match.groups():
            stylesheet = _clean_resource_reference(group)
            if stylesheet:
                stylesheets.add(stylesheet)
    return stylesheets


def _extract_scripts(html):
    scripts = set()
    for script_src in SCRIPT_PATTERN.findall(html or ""):
        script = _clean_resource_reference(script_src)
        if script:
            scripts.add(script)
    return scripts


def _read_referenced_script(script_src):
    parsed = urlparse(script_src)
    path = parsed.path.lstrip("/")
    if not path.startswith("js/"):
        return ""
    script_path = os.path.join(os.path.dirname(__file__), "static", *path.split("/"))
    if not os.path.exists(script_path):
        return ""
    try:
        with open(script_path, "r", encoding="utf-8", errors="ignore") as script_file:
            return script_file.read()
    except OSError:
        return ""


def _api_methods_for_path(api_path):
    parsed = urlparse(api_path)
    path = parsed.path or api_path
    ignored_methods = {"HEAD", "OPTIONS"}

    for rule in current_app.url_map.iter_rules():
        if rule.rule != path:
            continue
        methods = sorted(method for method in rule.methods if method not in ignored_methods)
        return ",".join(methods) if methods else "GET"
    return "API"


def _api_supports_get(api_path):
    return "GET" in _api_methods_for_path(api_path).split(",")


def _print_resource_group(title, resources):
    if title == "API":
        resources = [resource for resource in resources if _api_supports_get(resource)]

    if not resources:
        print(f"  [{title}] No detectado", flush=True)
        return

    for resource in sorted(resources):
        if title == "API":
            print(f"  [{title}] GET - {resource}", flush=True)
            continue
        print(f"  [{title}] {resource}", flush=True)


def _log_page_resources(path, html):
    stylesheets = _extract_stylesheets(html)
    scripts = _extract_scripts(html)
    apis = _extract_api_references(html)
    for script_src in scripts:
        apis.update(_extract_api_references(_read_referenced_script(script_src)))

    if not stylesheets and not scripts and not apis:
        return

    print(f"[APARTADO] {path} -> recursos obtenidos:", flush=True)
    _print_resource_group("CSS", stylesheets)
    _print_resource_group("JS", scripts)
    _print_resource_group("API", apis)


def _shorten_text(value, limit=500):
    text = str(value or "").replace("\n", " ").replace("\r", " ").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _extract_response_error(response):
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        payload = response.get_json(silent=True)
        if isinstance(payload, dict):
            message = payload.get("message") or payload.get("error") or payload.get("detail") or payload.get("status")
            if message:
                return _shorten_text(message)
            if payload.get("success") is False:
                return _shorten_text(payload)
        return None

    if response.status_code >= 400:
        return _shorten_text(response.get_data(as_text=True))
    return None


def _extract_response_summary(response):
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        payload = response.get_json(silent=True)
        if payload is not None:
            return _shorten_text(payload, 700)
    if response.status_code >= 400:
        return _shorten_text(response.get_data(as_text=True), 700)
    return None


def _redact_sensitive(value):
    sensitive_keys = {"password", "contrasena", "confirm_password", "new_password", "token"}
    if isinstance(value, dict):
        return {
            key: "***" if str(key).lower() in sensitive_keys else _redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    return value


def _log_api_error(request, response):
    is_api = request.path.startswith("/api/") or request.path == "/healthz"
    if not is_api:
        return

    payload = response.get_json(silent=True) if "application/json" in response.headers.get("Content-Type", "") else None
    reported_failure = isinstance(payload, dict) and payload.get("success") is False
    degraded_health = request.path == "/healthz" and response.status_code >= 400
    if response.status_code < 400 and not reported_failure and not degraded_health:
        return

    reason = _extract_response_error(response) or response.status
    print(
        f"[API ERROR] {request.method} - {response.status_code:>3} {request.path} -> {reason}",
        flush=True,
    )

    detail = getattr(g, "_api_error_detail", None)
    if detail:
        print(f"  [MOTIVO] {_shorten_text(detail, 700)}", flush=True)

    if request.query_string:
        print(f"  [QUERY] {_shorten_text(request.query_string.decode('utf-8', errors='ignore'))}", flush=True)

    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        body = request.get_json(silent=True)
        if body is None:
            body = request.form.to_dict() or request.get_data(as_text=True)
        if body:
            print(f"  [BODY] {_shorten_text(_redact_sensitive(body))}", flush=True)

    response_summary = _extract_response_summary(response)
    if response_summary and response_summary != reason:
        print(f"  [RESPUESTA] {response_summary}", flush=True)


def _client_error_reporter_script():
    return """
<script>
(function () {
  if (window.__psyaiErrorReporterInstalled) return;
  window.__psyaiErrorReporterInstalled = true;

  function describeReason(reason) {
    if (!reason) return "";
    if (reason.stack) return reason.stack;
    if (reason.message) return reason.message;
    try { return JSON.stringify(reason); } catch (_) { return String(reason); }
  }

  function sendClientError(type, message, details) {
    try {
      fetch("/api/client-errors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        keepalive: true,
        body: JSON.stringify({
          type: type,
          message: message || "",
          details: details || "",
          page: window.location.pathname + window.location.search
        })
      }).catch(function () {});
    } catch (_) {}
  }

  window.addEventListener("error", function (event) {
    sendClientError("javascript", event.message, [
      event.filename || "",
      event.lineno || "",
      event.colno || "",
      event.error && event.error.stack ? event.error.stack : ""
    ].filter(Boolean).join(" | "));
  });

  window.addEventListener("unhandledrejection", function (event) {
    sendClientError("promise", describeReason(event.reason), "");
  });
})();
</script>
""".strip()


def _inject_csrf_meta(response):
    """Inyecta meta tag CSRF y JS fetch interceptor en HTML."""
    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return response

    html = response.get_data(as_text=True)
    if 'name="csrf-token"' in html:
        return response

    from flask_wtf.csrf import generate_csrf
    try:
        token = generate_csrf()
    except Exception:
        token = ""

    script = f"""<meta name="csrf-token" content="{token}">
<script>
(function(){{
  var tokenMeta = document.querySelector('meta[name="csrf-token"]');
  if (!tokenMeta || window.__csrfInstalled) return;
  window.__csrfInstalled = true;
  var origFetch = window.fetch;
  window.fetch = function(url, opts) {{
    opts = opts || {{}};
    opts.headers = opts.headers || {{}};
    if (opts.method && opts.method.toUpperCase() !== 'GET') {{
      if (tokenMeta) opts.headers['X-CSRFToken'] = tokenMeta.getAttribute('content');
    }}
    return origFetch.call(this, url, opts);
  }};
}})();
</script>
"""
    updated = re.sub(r"<head[^>]*>", lambda m: m.group(0) + "\n" + script.strip(), html, count=1, flags=re.IGNORECASE)
    if updated == html:
        updated = re.sub(r"<html[^>]*>", lambda m: m.group(0) + "\n" + script.strip(), html, count=1, flags=re.IGNORECASE)
    if updated == html:
        updated = script.strip() + "\n" + html
    response.set_data(updated)
    response.headers["Content-Length"] = str(len(response.get_data()))
    return response


def _inject_client_error_reporter(response):
    content_type = response.headers.get("Content-Type", "")
    if response.status_code >= 400 or "text/html" not in content_type:
        return response

    html = response.get_data(as_text=True)
    if "__psyaiErrorReporterInstalled" in html or "</body>" not in html.lower():
        return response

    script = _client_error_reporter_script()
    updated = re.sub(r"</body>", script + "\n</body>", html, count=1, flags=re.IGNORECASE)
    response.set_data(updated)
    response.headers["Content-Length"] = str(len(response.get_data()))
    return response


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder=None,
    )
    app.config.from_object(Config)
    if app.config.get("FLASK_ENV") != "production":
        app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.secret_key = Config.SECRET_KEY

    setup_logging(app)
    init_pool(app)
    verificar_tablas(app)

    app.wsgi_app = RequestLoggingMiddleware(app.wsgi_app)

    Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=Config.RATELIMIT_STORAGE_URI,
    )

    def get_limiter():
        limiters = app.extensions.get("limiter", set())
        return next(iter(limiters)) if limiters else None

    app.get_limiter = get_limiter

    CORS(app, supports_credentials=True, origins=Config.CORS_ORIGINS)

    csrf = CSRFProtect(app)
    if not Config.WTF_CSRF_ENABLED:
        csrf.exempt(lambda: True)

    app.json_provider_class = CustomJSONProvider
    app.json = CustomJSONProvider(app)

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

    @app.route("/api/routes", methods=["GET"])
    def api_routes():
        ignored_methods = {"HEAD", "OPTIONS"}
        routes = []
        for rule in sorted(app.url_map.iter_rules(), key=lambda item: item.rule):
            if not rule.rule.startswith("/api/") and rule.rule != "/healthz":
                continue
            routes.append(
                {
                    "methods": sorted(method for method in rule.methods if method not in ignored_methods),
                    "path": rule.rule,
                    "endpoint": rule.endpoint,
                }
            )
        return jsonify({"success": True, "count": len(routes), "routes": routes})

    @app.route("/api/client-errors", methods=["POST"])
    @csrf.exempt
    def client_errors():
        payload = request.get_json(silent=True) or {}
        error_type = _shorten_text(payload.get("type") or "javascript", 80)
        page = _shorten_text(payload.get("page") or request.headers.get("Referer") or "pagina desconocida", 200)
        message = _shorten_text(payload.get("message") or "Error sin mensaje", 400)
        details = _shorten_text(payload.get("details"), 500)

        print(f"[PAGINA ERROR] {error_type} {page} -> {message}", flush=True)
        if details:
            print(f"  [DETALLE] {details}", flush=True)

        return "", 204

    @app.before_request
    def telemetry_hook():
        import time as _time
        from flask import request, g
        g._telemetry_start = _time.time()
        if request.path.startswith("/css/") or request.path.startswith("/js/") or request.path.startswith("/img/"):
            return
        track_request(get_remote_address(), request.path, session.get("idUsuario"))

    @app.after_request
    def telemetry_latency(response):
        import time as _time
        from flask import g, request

        # Security headers
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-XSS-Protection", "0")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com 'unsafe-inline'; "
            "style-src 'self' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com https://fonts.googleapis.com 'unsafe-inline'; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'",
        )
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        start = getattr(g, "_telemetry_start", None)
        if start:
            duration_ms = (_time.time() - start) * 1000
            track_latency(duration_ms)
        content_type = response.headers.get("Content-Type", "")
        if response.status_code < 400 and "text/html" in content_type:
            try:
                _log_page_resources(request.path, response.get_data(as_text=True))
            except Exception as exc:
                app.logger.warning("No se pudieron detectar recursos para %s: %s", request.path, exc)
            response = _inject_csrf_meta(response)
            response = _inject_client_error_reporter(response)
        try:
            _log_api_error(request, response)
        except Exception as exc:
            app.logger.warning("No se pudo imprimir error API para %s: %s", request.path, exc)
        return response

    @app.errorhandler(404)
    def handle_404(error):
        from flask import request
        g._api_error_detail = "La ruta no existe o no esta registrada en Flask."
        app.logger.error("404 NOT FOUND: %s %s", request.method, request.path)
        return jsonify({"success": False, "message": "Recurso no encontrado"}), 404

    @app.errorhandler(500)
    def handle_500(error):
        from flask import request
        g._api_error_detail = f"Error interno del servidor: {error}"
        app.logger.error("500 SERVER ERROR: %s %s - %s", request.method, request.path, error, exc_info=True)
        return jsonify({"success": False, "message": "Error interno del servidor"}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        from flask import request
        if isinstance(error, HTTPException):
            g._api_error_detail = f"HTTP {error.code}: {error.description}"
            app.logger.warning("Error HTTP %s: %s %s", error.code, request.method, request.path)
            return jsonify({"success": False, "message": error.description}), error.code
        g._api_error_detail = f"{type(error).__name__}: {error}"
        app.logger.error("EXCEPCION NO CONTROLADA: %s %s - %s", request.method, request.path, error, exc_info=True)
        return jsonify({"success": False, "message": "Error interno del servidor"}), 500

    return app
