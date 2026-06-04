import logging
import os
import sys
import time

from dotenv import load_dotenv
import flask.cli


BOOT_STARTED_AT = time.perf_counter()
BASE_DIR = os.path.dirname(__file__)
env_path = os.path.join(BASE_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(BASE_DIR, ".env.example")
load_dotenv(env_path)


def configure_terminal_logging():
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

    log_level_name = os.getenv("LOG_LEVEL", "ERROR").upper()
    log_level = getattr(logging, log_level_name, logging.ERROR)
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )

    for logger_name in ("flask.app", "app"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.propagate = True

    werkzeug_level = logging.INFO if os.getenv("SHOW_WERKZEUG_LOGS", "0") == "1" else logging.WARNING
    for logger_name in ("werkzeug", "werkzeug.serving"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.setLevel(werkzeug_level)
        logger.propagate = True

    if os.getenv("LOG_THIRD_PARTY_DEBUG", "0") != "1":
        logging.getLogger("mysql.connector").setLevel(logging.WARNING)
        logging.getLogger("flask-limiter").setLevel(logging.WARNING)


def get_registered_routes(flask_app):
    ignored_methods = {"HEAD", "OPTIONS"}
    routes = []
    for rule in sorted(flask_app.url_map.iter_rules(), key=lambda item: item.rule):
        methods = sorted(method for method in rule.methods if method not in ignored_methods)
        route_type = "API" if rule.rule.startswith("/api/") or rule.rule == "/healthz" else "PAGE"
        routes.append(
            {
                "methods": methods,
                "path": rule.rule,
                "endpoint": rule.endpoint,
                "type": route_type,
            }
        )
    return routes


def print_route_section(title, routes):
    print(f"\n--- {title} ---", flush=True)
    if not routes:
        print("  No hay rutas registradas.", flush=True)
        return

    for route in routes:
        methods = ",".join(route["methods"])
        print(f"  {methods:18} {route['path']:<55} -> {route['endpoint']}", flush=True)


def print_app_info(flask_app):
    routes = get_registered_routes(flask_app)
    api_routes = [route for route in routes if route["type"] == "API"]

    print("\n" + "=" * 60, flush=True)
    print("PsyAI Connect - APIs REST y errores", flush=True)
    print("=" * 60, flush=True)
    print_route_section("APIs REST registradas", api_routes)
    print("\n" + "=" * 60, flush=True)


def hide_flask_banner():
    flask.cli.show_server_banner = lambda *args, **kwargs: None


configure_terminal_logging()

from app import create_app  # noqa: E402
from app.database.migrations import init_db  # noqa: E402


app = create_app()
app.config["REGISTERED_ROUTES"] = get_registered_routes(app)

with app.app_context():
    try:
        init_db()
    except Exception as exc:
        app.logger.exception("No se pudo inicializar la base de datos: %s", exc)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_enabled = os.getenv("FLASK_DEBUG", "0") == "1"
    boot_ms = (time.perf_counter() - BOOT_STARTED_AT) * 1000

    hide_flask_banner()
    print_app_info(app)
    print("\n" + "=" * 60, flush=True)
    print(f"[INICIO] Servidor preparado en {boot_ms:.1f} ms", flush=True)
    print(f"Servidor iniciado en: http://127.0.0.1:{port}", flush=True)
    print(f"Listado JSON de APIs: http://127.0.0.1:{port}/api/routes", flush=True)
    print("Terminal: recursos por apartado, acciones REST y errores de pagina", flush=True)
    print("=" * 60 + "\n", flush=True)

    app.run(
        debug=debug_enabled,
        host="127.0.0.1",
        port=port,
        use_reloader=False,
        use_evalex=False,
        threaded=True,
    )
