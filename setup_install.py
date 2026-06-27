"""
setup_install.py — PsyAI Connect
=================================
Ejecuta una sola vez para dejar el proyecto 100% listo:
  - Crea el venv si no existe
  - Instala dependencias globalmente Y en el venv
  - Crea/actualiza el .env con todas las credenciales

Uso:  python setup_install.py
"""

import os
import secrets
import subprocess
import sys
from pathlib import Path

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
VENV_DIR = BASE_DIR / "venv"
ENV_FILE  = BASE_DIR / ".env"
REQ_FILE  = BASE_DIR / "requirements.txt"

# ── Colores ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):    print(f"{GREEN}  ✅ {msg}{RESET}")
def warn(msg):  print(f"{YELLOW}  ⚠️  {msg}{RESET}")
def err(msg):   print(f"{RED}  ❌ {msg}{RESET}")
def info(msg):  print(f"{CYAN}  ›  {msg}{RESET}")
def title(msg): print(f"\n{BOLD}{'═'*52}\n  {msg}\n{'═'*52}{RESET}")


# ── Credenciales del proyecto ─────────────────────────────────────────────────
# Edita estos valores si cambian en el futuro.
CREDENTIALS: dict[str, str] = {
    # Flask
    "SECRET_KEY":               "fee3886d1a38c243472705ddc4b2c08e239134ecf9015030a7e812204202233f",
    "FLASK_ENV":                "development",
    "PORT":                     "5000",
    "FLASK_DEBUG":              "0",
    "SHOW_WERKZEUG_LOGS":       "0",
    "LOG_THIRD_PARTY_DEBUG":    "0",

    # Base de datos MySQL (XAMPP)
    "DB_HOST":                  "localhost",
    "DB_PORT":                  "3306",
    "DB_USER":                  "root",
    "DB_PASSWORD":              "root",
    "DB_NAME":                  "psyai_connect",

    # Pool de conexiones
    "DB_POOL_NAME":             "psyai_pool",
    "DB_POOL_SIZE":             "5",
    "DB_POOL_RESET_SESSION":    "true",

    # Gemini AI
    # Para activar rotación de keys en el futuro:
    #   GEMINI_API_KEYS=key1,key2,key3,...
    "GEMINI_API_KEY":           "AIzaSyDbXVQ_QlYlD5tcn6O3gEADXotzHFo4V7M",
    "GEMINI_API_KEYS":          "",   # vacío = usa solo GEMINI_API_KEY
    "GEMINI_MODEL":             "gemini-2.5-flash-lite",

    # Resend (emails)
    "BREVO_API_KEY":            "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",
    "BREVO_FROM":               "manuelrojasq21@gmail.com",
    "BREVO_FROM_NAME":          "PsyAI Connect",

    # Logs
    "LOG_LEVEL":                "ERROR",
    "LOG_FORMAT":               "werkzeug",

    # Rate Limiting
    "RATELIMIT_STORAGE_URI":    "memory://",

    # CORS
    "CORS_ORIGINS":             "http://localhost:5000,http://127.0.0.1:5000,https://psyai-connect.com",

    # Session
    "SESSION_COOKIE_SECURE":    "False",
    "SESSION_COOKIE_HTTPONLY":  "True",
    "SESSION_COOKIE_SAMESITE":  "Lax",
}

# Secciones para organizar el .env generado
ENV_SECTIONS: list[tuple[str, list[str]]] = [
    ("Flask", [
        "SECRET_KEY", "FLASK_ENV", "PORT",
        "FLASK_DEBUG", "SHOW_WERKZEUG_LOGS", "LOG_THIRD_PARTY_DEBUG",
    ]),
    ("Base de datos MySQL (XAMPP)", [
        "DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME",
    ]),
    ("Pool de conexiones", [
        "DB_POOL_NAME", "DB_POOL_SIZE", "DB_POOL_RESET_SESSION",
    ]),
    ("Gemini AI", [
        "GEMINI_API_KEY", "GEMINI_API_KEYS", "GEMINI_MODEL",
    ]),
    ("Resend (emails)", [
        "BREVO_API_KEY", "BREVO_FROM", "BREVO_FROM_NAME",
    ]),
    ("Logs", [
        "LOG_LEVEL", "LOG_FORMAT",
    ]),
    ("Rate Limiting", [
        "RATELIMIT_STORAGE_URI",
    ]),
    ("CORS Origins", [
        "CORS_ORIGINS",
    ]),
    ("Session Settings", [
        "SESSION_COOKIE_SECURE", "SESSION_COOKIE_HTTPONLY", "SESSION_COOKIE_SAMESITE",
    ]),
]


# ── Venv ──────────────────────────────────────────────────────────────────────

def ensure_venv():
    title("ENTORNO VIRTUAL")
    if VENV_DIR.exists():
        ok(f"venv ya existe → {VENV_DIR}")
        return
    info("Creando venv...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        ok(f"venv creado → {VENV_DIR}")
    except subprocess.CalledProcessError:
        err("No se pudo crear el venv.")
        sys.exit(1)


def _pip(target: str) -> list[str]:
    """Retorna el comando pip para 'global' o 'venv'."""
    if target == "global":
        return [sys.executable, "-m", "pip"]
    if sys.platform == "win32":
        pip = VENV_DIR / "Scripts" / "pip.exe"
    else:
        pip = VENV_DIR / "bin" / "pip"
    return [str(pip)] if pip.exists() else []


def _python_venv() -> list[str]:
    if sys.platform == "win32":
        py = VENV_DIR / "Scripts" / "python.exe"
    else:
        py = VENV_DIR / "bin" / "python"
    return [str(py)] if py.exists() else []


# ── Instalación ───────────────────────────────────────────────────────────────

def _read_packages() -> list[str]:
    if REQ_FILE.exists():
        pkgs = []
        for line in REQ_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pkgs.append(line)
        return pkgs
    warn("requirements.txt no encontrado — usando lista mínima.")
    return [
        "flask>=3.0.0", "flask-cors>=4.0.0", "flask-limiter>=3.0.0",
        "mysql-connector-python>=8.0.0", "python-dotenv>=1.0.0",
        "waitress>=2.1.0", "filetype>=1.2.0", "psutil>=5.9.0",
        "requests>=2.31.0", "bcrypt>=4.0.0",
    ]


def _install_packages(pip_cmd: list[str], label: str, packages: list[str]):
    if not pip_cmd:
        warn(f"[{label}] pip no disponible — saltando.")
        return
    for pkg in packages:
        pkg_name = pkg.split(">=")[0].split("==")[0].split("[")[0].strip()
        shown = subprocess.run(
            pip_cmd + ["show", pkg_name],
            capture_output=True, text=True,
        )
        if shown.returncode == 0:
            warn(f"[{label}] {pkg_name} ya instalado")
        else:
            try:
                subprocess.check_call(
                    pip_cmd + ["install", pkg, "--quiet"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                ok(f"[{label}] {pkg_name} instalado")
            except subprocess.CalledProcessError:
                err(f"[{label}] No se pudo instalar {pkg_name}")


def install_dependencies():
    title("INSTALACIÓN DE DEPENDENCIAS")
    packages = _read_packages()

    info("Instalando globalmente...")
    _install_packages(_pip("global"), "global", packages)

    info("Instalando en venv...")
    _install_packages(_pip("venv"), "venv", packages)


# ── .env ──────────────────────────────────────────────────────────────────────

def _read_existing_env() -> dict[str, str]:
    """Lee el .env actual para no pisar valores que el usuario haya editado a mano."""
    existing: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
    return existing


def _write_env(final: dict[str, str]):
    lines = [
        "# PsyAI Connect — generado automáticamente por setup_install.py",
        "# No edites manualmente salvo que sepas lo que haces.",
        "",
    ]
    written: set[str] = set()

    for section_name, keys in ENV_SECTIONS:
        separator = "─" * (46 - len(section_name))
        lines.append(f"# ── {section_name} {separator}")
        for k in keys:
            if k in final:
                lines.append(f"{k}={final[k]}")
                written.add(k)
        lines.append("")

    # Claves no previstas en secciones (forward-compat)
    extras = [k for k in final if k not in written]
    if extras:
        lines.append("# ── Otros ───────────────────────────────────────")
        for k in extras:
            lines.append(f"{k}={final[k]}")
        lines.append("")

    ENV_FILE.write_text("\n".join(lines), encoding="utf-8")


def configure_env():
    title("CONFIGURACIÓN DEL .env")

    existing = _read_existing_env()

    # Merge: valores existentes tienen prioridad sobre CREDENTIALS,
    # excepto SECRET_KEY que siempre respetamos si ya existe.
    final: dict[str, str] = dict(CREDENTIALS)  # base con las credenciales del proyecto
    for k, v in existing.items():
        if v:  # si ya tenía valor en el .env, lo respetamos
            final[k] = v

    # SECRET_KEY: si no existe en ningún lado, generamos uno nuevo
    if not final.get("SECRET_KEY") or final["SECRET_KEY"] == "cambia_esto_por_una_clave_segura":
        final["SECRET_KEY"] = secrets.token_hex(32)
        info("SECRET_KEY generado automáticamente")

    # GEMINI_API_KEYS: si está vacío, omitir la línea del .env para no confundir
    if not final.get("GEMINI_API_KEYS"):
        final["GEMINI_API_KEYS"] = ""  # se escribe como vacío, el código lo ignora

    _write_env(final)
    ok(f".env escrito → {ENV_FILE}")

    # Mostrar resumen (sin exponer valores secretos)
    secret_keys = {"SECRET_KEY", "GEMINI_API_KEY", "GEMINI_API_KEYS", "BREVO_API_KEY", "DB_PASSWORD"}
    print()
    for section_name, keys in ENV_SECTIONS:
        print(f"  {CYAN}{section_name}{RESET}")
        for k in keys:
            v = final.get(k, "")
            display = ("***" if v else "(vacío)") if k in secret_keys else (v or "(vacío)")
            print(f"    {k} = {display}")
        print()


# ── Verificación ──────────────────────────────────────────────────────────────

def verify() -> bool:
    title("VERIFICACIÓN FINAL")

    required = {
        "SECRET_KEY":     "Flask",
        "DB_HOST":        "Base de datos",
        "DB_NAME":        "Base de datos",
        "GEMINI_API_KEY": "Gemini AI",
        "GEMINI_MODEL":   "Gemini AI",
        "BREVO_API_KEY": "Brevo",
        "BREVO_FROM":    "Brevo",
        "BREVO_FROM_NAME": "Brevo",
    }

    env = _read_existing_env()
    all_ok = True
    for key, section in required.items():
        v = env.get(key, "")
        if v and v not in ("cambia_esto_por_una_clave_segura", ""):
            ok(f"{key}  ({section})")
        else:
            warn(f"{key}  ({section}) — falta o sin valor")
            all_ok = False

    # Flask en venv
    py_venv = _python_venv()
    if py_venv:
        result = subprocess.run(
            py_venv + ["-c", "import flask; print(flask.__version__)"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            ok(f"Flask en venv: v{result.stdout.strip()}")
        else:
            warn("Flask no detectado en venv — revisa la instalación")
            all_ok = False
    else:
        warn("Python del venv no encontrado")
        all_ok = False

    return all_ok


# ── Banner ────────────────────────────────────────────────────────────────────

def print_banner(success: bool):
    print()
    if success:
        color = GREEN
        lines = [
            "  PsyAI Connect — Setup completado ✅  ",
            "                                       ",
            "  Iniciar servidor:                    ",
            "    python run.py                      ",
            "                                       ",
            "  O con el venv activado:              ",
            "    venv\\Scripts\\activate  (Windows)   ",
            "    source venv/bin/activate (Linux)   ",
            "    python run.py                      ",
        ]
    else:
        color = YELLOW
        lines = [
            "  Setup completado con advertencias ⚠️  ",
            "  Revisa los items marcados arriba.    ",
            "  Luego corre:  python run.py          ",
        ]
    width = max(len(l) for l in lines) + 2
    print(f"{color}╔{'═'*width}╗{RESET}")
    for l in lines:
        print(f"{color}║ {l:<{width-1}}║{RESET}")
    print(f"{color}╚{'═'*width}╝{RESET}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}  PsyAI Connect — Instalador automático{RESET}\n")
    ensure_venv()
    install_dependencies()
    configure_env()
    success = verify()
    print_banner(success)


if __name__ == "__main__":
    main()
