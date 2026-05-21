"""
setup_install.py — PsyAI Connect
=================================
Instala dependencias globalmente Y en el venv al mismo tiempo,
luego configura todas las credenciales del .env de forma interactiva.

Uso:
    python setup_install.py
"""

import os
import secrets
import subprocess
import sys
from pathlib import Path

# ── Rutas base ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.resolve()
VENV_DIR   = BASE_DIR / "venv"
ENV_FILE   = BASE_DIR / ".env"
REQ_FILE   = BASE_DIR / "requirements.txt"

# ── Colores de consola (Windows compatible) ───────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def c(color, text): return f"{color}{text}{RESET}"
def ok(msg):   print(c(GREEN,  f"  ✅ {msg}"))
def warn(msg): print(c(YELLOW, f"  ⚠️  {msg}"))
def err(msg):  print(c(RED,    f"  ❌ {msg}"))
def info(msg): print(c(CYAN,   f"  ℹ️  {msg}"))
def title(msg):print(c(BOLD,   f"\n{'═'*50}\n  {msg}\n{'═'*50}"))


# ── Detectar ejecutables pip ──────────────────────────────────────────────────

def _pip_global() -> list[str]:
    """Retorna el comando pip del Python global (el que corre este script)."""
    return [sys.executable, "-m", "pip"]


def _pip_venv() -> list[str] | None:
    """Retorna el comando pip del venv si existe, si no None."""
    if sys.platform == "win32":
        pip = VENV_DIR / "Scripts" / "pip.exe"
    else:
        pip = VENV_DIR / "bin" / "pip"
    return [str(pip)] if pip.exists() else None


def _python_venv() -> list[str] | None:
    if sys.platform == "win32":
        py = VENV_DIR / "Scripts" / "python.exe"
    else:
        py = VENV_DIR / "bin" / "python"
    return [str(py)] if py.exists() else None


# ── Creación del venv ─────────────────────────────────────────────────────────

def ensure_venv():
    title("ENTORNO VIRTUAL")
    if VENV_DIR.exists():
        ok(f"venv ya existe en {VENV_DIR}")
        return
    info("Creando venv...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        ok(f"venv creado en {VENV_DIR}")
    except subprocess.CalledProcessError:
        err("No se pudo crear el venv. Asegúrate de tener 'python -m venv' disponible.")
        sys.exit(1)


# ── Instalación de paquetes ───────────────────────────────────────────────────

def _install_with(pip_cmd: list[str], label: str, packages: list[str]):
    """Instala una lista de paquetes con el pip dado."""
    for pkg in packages:
        result = subprocess.run(
            pip_cmd + ["show", pkg.split(">=")[0].split("==")[0].strip()],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            warn(f"[{label}] {pkg} ya instalado")
        else:
            try:
                subprocess.check_call(
                    pip_cmd + ["install", pkg, "--quiet"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                ok(f"[{label}] {pkg} instalado")
            except subprocess.CalledProcessError:
                err(f"[{label}] No se pudo instalar {pkg}")


def install_dependencies():
    title("INSTALACIÓN DE DEPENDENCIAS")

    # Leer requirements.txt
    packages = []
    if REQ_FILE.exists():
        for line in REQ_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                packages.append(line)
    else:
        warn("requirements.txt no encontrado, usando lista mínima.")
        packages = [
            "flask>=3.0.0",
            "flask-cors>=4.0.0",
            "flask-limiter>=3.0.0",
            "mysql-connector-python>=8.0.0",
            "python-dotenv>=1.0.0",
            "waitress>=2.1.0",
            "filetype>=1.2.0",
            "psutil>=5.9.0",
            "requests>=2.31.0",
            "bcrypt>=4.0.0",
        ]

    # 1. Global (Python que corre este script)
    info("Instalando globalmente...")
    _install_with(_pip_global(), "global", packages)

    # 2. Venv
    pip_venv = _pip_venv()
    if pip_venv:
        info("Instalando en venv...")
        _install_with(pip_venv, "venv", packages)
    else:
        warn("venv/pip no encontrado — saltando instalación en venv.")


# ── Helpers para .env ─────────────────────────────────────────────────────────

def _load_env() -> dict[str, str]:
    """Lee el .env actual como dict (preserva orden y comentarios no)."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _save_env(env: dict[str, str]):
    """Escribe el .env completo desde el dict, con secciones comentadas."""
    sections = {
        "Flask": ["SECRET_KEY", "FLASK_ENV", "PORT", "FLASK_DEBUG",
                  "SHOW_WERKZEUG_LOGS", "LOG_THIRD_PARTY_DEBUG"],
        "Base de datos MySQL (XAMPP)": ["DB_HOST", "DB_PORT", "DB_USER",
                                         "DB_PASSWORD", "DB_NAME"],
        "Pool de conexiones": ["DB_POOL_NAME", "DB_POOL_SIZE", "DB_POOL_RESET_SESSION"],
        "Gemini AI": ["GEMINI_API_KEY", "GEMINI_API_KEYS", "GEMINI_MODEL"],
        "Resend (email)": ["RESEND_API_KEY", "SMTP_FROM"],
        "Logs": ["LOG_LEVEL", "LOG_FORMAT"],
        "Rate Limiting": ["RATELIMIT_STORAGE_URI"],
        "CORS Origins": ["CORS_ORIGINS"],
        "Session Settings": ["SESSION_COOKIE_SECURE", "SESSION_COOKIE_HTTPONLY",
                              "SESSION_COOKIE_SAMESITE"],
    }

    lines = ["# PsyAI Connect — .env generado por setup_install.py", ""]
    written = set()

    for section, keys in sections.items():
        lines.append(f"# --- {section} {'─'*(40-len(section))-2 if len(section)<38 else ''}")
        for k in keys:
            if k in env:
                lines.append(f"{k}={env[k]}")
                written.add(k)
        lines.append("")

    # Claves extra no contempladas en secciones
    extras = [k for k in env if k not in written]
    if extras:
        lines.append("# --- Otros ---")
        for k in extras:
            lines.append(f"{k}={env[k]}")
        lines.append("")

    ENV_FILE.write_text("\n".join(lines), encoding="utf-8")


def _ask(prompt: str, default: str = "", secret: bool = False) -> str:
    """Pide input al usuario. Si presiona Enter, usa el default."""
    display_default = "***" if secret and default else default
    suffix = f" [{display_default}]" if default else ""
    try:
        value = input(f"    {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return value if value else default


def _ask_bool(prompt: str, default: bool = False) -> str:
    default_str = "True" if default else "False"
    val = _ask(prompt, default_str)
    return "True" if val.lower() in ("true", "1", "si", "sí", "yes", "y") else "False"


# ── Configuración interactiva del .env ────────────────────────────────────────

def configure_env():
    title("CONFIGURACIÓN DE CREDENCIALES (.env)")
    env = _load_env()

    # ── Flask ────────────────────────────────────────────────────────────────
    print(c(CYAN, "\n  [Flask]"))
    if not env.get("SECRET_KEY"):
        env["SECRET_KEY"] = secrets.token_hex(32)
        ok("SECRET_KEY generado automáticamente")
    else:
        ok("SECRET_KEY ya existe")

    env.setdefault("FLASK_ENV", "development")
    flask_env = _ask("Entorno Flask (development/production)", env["FLASK_ENV"])
    env["FLASK_ENV"] = flask_env

    env.setdefault("PORT", "5000")
    env["PORT"] = _ask("Puerto del servidor", env["PORT"])

    env.setdefault("FLASK_DEBUG", "0")
    env.setdefault("SHOW_WERKZEUG_LOGS", "0")
    env.setdefault("LOG_THIRD_PARTY_DEBUG", "0")

    # ── Base de datos ────────────────────────────────────────────────────────
    print(c(CYAN, "\n  [Base de datos MySQL]"))
    env["DB_HOST"]     = _ask("Host DB",     env.get("DB_HOST", "localhost"))
    env["DB_PORT"]     = _ask("Puerto DB",   env.get("DB_PORT", "3306"))
    env["DB_USER"]     = _ask("Usuario DB",  env.get("DB_USER", "root"))
    env["DB_PASSWORD"] = _ask("Password DB", env.get("DB_PASSWORD", ""), secret=True)
    env["DB_NAME"]     = _ask("Nombre DB",   env.get("DB_NAME", "psyai_connect"))

    env.setdefault("DB_POOL_NAME",          "psyai_pool")
    env.setdefault("DB_POOL_SIZE",          "5")
    env.setdefault("DB_POOL_RESET_SESSION", "true")

    # ── Gemini AI ────────────────────────────────────────────────────────────
    print(c(CYAN, "\n  [Gemini AI]"))
    info("GEMINI_API_KEY  → una sola key (uso actual)")
    info("GEMINI_API_KEYS → varias keys separadas por coma (rotación automática)")

    env["GEMINI_API_KEY"] = _ask(
        "GEMINI_API_KEY (key principal)",
        env.get("GEMINI_API_KEY", ""), secret=True
    )
    env["GEMINI_API_KEYS"] = _ask(
        "GEMINI_API_KEYS (opcional, ej: key1,key2,key3)",
        env.get("GEMINI_API_KEYS", "")
    )
    env["GEMINI_MODEL"] = _ask(
        "Modelo Gemini",
        env.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    )

    # ── Resend ───────────────────────────────────────────────────────────────
    print(c(CYAN, "\n  [Resend — envío de emails]"))
    env["RESEND_API_KEY"] = _ask(
        "RESEND_API_KEY",
        env.get("RESEND_API_KEY", ""), secret=True
    )
    env["SMTP_FROM"] = _ask(
        "Email remitente",
        env.get("SMTP_FROM", "")
    )

    # ── Logs ─────────────────────────────────────────────────────────────────
    print(c(CYAN, "\n  [Logs]"))
    env["LOG_LEVEL"]  = _ask("Nivel de log (DEBUG/INFO/WARNING/ERROR)", env.get("LOG_LEVEL",  "ERROR"))
    env["LOG_FORMAT"] = _ask("Formato log (werkzeug/json)",             env.get("LOG_FORMAT", "werkzeug"))

    # ── Rate limiting ────────────────────────────────────────────────────────
    env.setdefault("RATELIMIT_STORAGE_URI", "memory://")

    # ── CORS ─────────────────────────────────────────────────────────────────
    print(c(CYAN, "\n  [CORS]"))
    env["CORS_ORIGINS"] = _ask(
        "Orígenes permitidos (separados por coma)",
        env.get("CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000")
    )

    # ── Session ──────────────────────────────────────────────────────────────
    env.setdefault("SESSION_COOKIE_SECURE",   "False")
    env.setdefault("SESSION_COOKIE_HTTPONLY", "True")
    env.setdefault("SESSION_COOKIE_SAMESITE", "Lax")

    _save_env(env)
    ok(f".env guardado en {ENV_FILE}")


# ── Verificación final ────────────────────────────────────────────────────────

def verify():
    title("VERIFICACIÓN FINAL")
    env = _load_env()

    checks = {
        "SECRET_KEY":     ("Flask",    bool(env.get("SECRET_KEY"))),
        "DB_HOST":        ("DB",       bool(env.get("DB_HOST"))),
        "DB_NAME":        ("DB",       bool(env.get("DB_NAME"))),
        "GEMINI_API_KEY": ("Gemini",   bool(env.get("GEMINI_API_KEY"))),
        "GEMINI_MODEL":   ("Gemini",   bool(env.get("GEMINI_MODEL"))),
        "RESEND_API_KEY": ("Resend",   bool(env.get("RESEND_API_KEY"))),
        "SMTP_FROM":      ("Resend",   bool(env.get("SMTP_FROM"))),
    }

    all_ok = True
    for key, (section, present) in checks.items():
        if present:
            ok(f"{key} ({section})")
        else:
            warn(f"{key} ({section}) — no configurado")
            all_ok = False

    # Verificar venv tiene Flask
    py_venv = _python_venv()
    if py_venv:
        result = subprocess.run(
            py_venv + ["-c", "import flask; print(flask.__version__)"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            ok(f"Flask en venv: v{result.stdout.strip()}")
        else:
            warn("Flask no detectado en venv")
    return all_ok


# ── Banner final ──────────────────────────────────────────────────────────────

def print_banner(success: bool):
    print()
    if success:
        print(c(GREEN, "╔══════════════════════════════════════╗"))
        print(c(GREEN, "║   PsyAI Connect — Setup completado   ║"))
        print(c(GREEN, "║                                      ║"))
        print(c(GREEN, "║   Para iniciar:  python run.py       ║"))
        print(c(GREEN, "║   O con venv:    venv\\Scripts\\python run.py  ║"))
        print(c(GREEN, "╚══════════════════════════════════════╝"))
    else:
        print(c(YELLOW, "╔══════════════════════════════════════╗"))
        print(c(YELLOW, "║   Setup completado con advertencias  ║"))
        print(c(YELLOW, "║   Revisa los ⚠️  antes de iniciar    ║"))
        print(c(YELLOW, "║   Para iniciar:  python run.py       ║"))
        print(c(YELLOW, "╚══════════════════════════════════════╝"))
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(c(BOLD, "\n  PsyAI Connect — Instalador y configurador\n"))

    ensure_venv()
    install_dependencies()
    configure_env()
    success = verify()
    print_banner(success)


if __name__ == "__main__":
    main()