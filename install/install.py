#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
PsyAI Connect — Instalador de entorno virtual y dependencias
═══════════════════════════════════════════════════════════════════════════

Uso (desde la raíz del proyecto):

    python install/install.py

Qué hace:
    1. Verifica Python ≥ 3.10
    2. Crea el entorno virtual `venv/` en la raíz (si no existe)
    3. Actualiza pip dentro del entorno
    4. Instala las dependencias de `requirements.txt`
    5. Abre una terminal con el entorno virtual ya activado

Opciones:
    --no-shell     Instala dependencias pero NO abre la terminal
    --recreate     Borra el entorno virtual actual y lo crea desde cero
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ── Rutas del proyecto ───────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / "venv"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
ENV_FILE = PROJECT_ROOT / ".env"

IS_WINDOWS = os.name == "nt"
MIN_PYTHON = (3, 10)


# ── Utilidades de consola ────────────────────────────────────────────────────
def banner() -> None:
    line = "=" * 72
    print(f"\n{line}")
    print("  PsyAI Connect - Instalador automatico")
    print(line)


def step(msg: str) -> None:
    print(f"  > {msg}")


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"\n  [ERROR] {msg}\n", file=sys.stderr)


def info(msg: str) -> None:
    print(f"  -> {msg}")


def header(title: str) -> None:
    line = "=" * 72
    print(f"\n{line}")
    print(f"  {title}")
    print(line)


# ── Helpers de rutas del venv ────────────────────────────────────────────────
def venv_scripts_dir() -> Path:
    return VENV_DIR / ("Scripts" if IS_WINDOWS else "bin")


def venv_python() -> Path:
    name = "python.exe" if IS_WINDOWS else "python"
    return venv_scripts_dir() / name


def venv_pip() -> Path:
    name = "pip.exe" if IS_WINDOWS else "pip"
    return venv_scripts_dir() / name


def activate_script() -> Path:
    if IS_WINDOWS:
        return venv_scripts_dir() / "activate.bat"
    return venv_scripts_dir() / "activate"


# ── Comprobaciones previas ───────────────────────────────────────────────────
def check_python_version() -> bool:
    if sys.version_info < MIN_PYTHON:
        error(
            f"Se requiere Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ "
            f"(actual: {sys.version_info.major}.{sys.version_info.minor})"
        )
        return False
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor} detectado")
    return True


def check_requirements() -> bool:
    if not REQUIREMENTS.exists():
        error(f"No se encontró {REQUIREMENTS}")
        return False
    ok("requirements.txt encontrado")
    return True


# ── Crear / recrear entorno virtual ──────────────────────────────────────────
def create_venv(recreate: bool) -> bool:
    if VENV_DIR.exists():
        if recreate:
            step("Borrando entorno virtual anterior...")
            shutil.rmtree(VENV_DIR)
        else:
            ok(f"Entorno virtual ya existe en {VENV_DIR}")
            return True

    step(f"Creando entorno virtual en {VENV_DIR}...")
    result = subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)])
    if result.returncode != 0:
        error("No se pudo crear el entorno virtual")
        return False
    ok("Entorno virtual creado")
    return True


# ── Instalar dependencias ────────────────────────────────────────────────────
def upgrade_pip() -> bool:
    step("Actualizando pip...")
    result = subprocess.run(
        [str(venv_python()), "-m", "pip", "install", "--upgrade", "pip", "--quiet"]
    )
    if result.returncode != 0:
        warn("No se pudo actualizar pip (continuando)")
        return False
    ok("pip actualizado")
    return True


def install_deps() -> bool:
    step("Instalando dependencias desde requirements.txt...")
    result = subprocess.run(
        [str(venv_python()), "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    )
    if result.returncode != 0:
        error(
            "Falló la instalación de dependencias.\n"
            "  • En Windows: mysqlclient puede requerir wheels o "
            "Microsoft Visual C++ Build Tools.\n"
            "  • En Linux: instale pkg-config y default-libmysqlclient-dev."
        )
        return False
    ok("Dependencias instaladas")
    return True


def verify_install() -> None:
    step("Verificando instalación...")
    result = subprocess.run(
        [str(venv_python()), "-m", "pip", "check"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        ok("pip check: sin conflictos")
    else:
        warn(f"pip check reportó:\n{result.stdout.strip()}")


# ── Abrir terminal con el venv activado ──────────────────────────────────────
def open_activated_shell() -> int:
    """Lanza una shell interactiva con el entorno virtual activado."""
    scripts = venv_scripts_dir()
    act = activate_script()

    header("Abriendo terminal con entorno activado")

    if IS_WINDOWS:
        # Preferir PowerShell si estamos en él (PSModulePath existe)
        if os.environ.get("PSModulePath"):
            ps_activate = scripts / "Activate.ps1"
            pwsh = shutil.which("pwsh") or shutil.which("powershell")
            if pwsh and ps_activate.exists():
                info("Detectado PowerShell → usando Activate.ps1")
                return subprocess.call(
                    [
                        pwsh,
                        "-NoExit",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-Command",
                        f"& '{ps_activate}'",
                    ],
                    cwd=PROJECT_ROOT,
                )
        # Fallback: cmd.exe clásico
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        info("Usando cmd.exe → activate.bat")
        return subprocess.call(
            [comspec, "/k", f'call "{act}"'],
            cwd=PROJECT_ROOT,
        )

    # ── Unix (Linux/macOS) ──────────────────────────────────────────────────
    shell = os.environ.get("SHELL", "/bin/bash")
    shell_name = Path(shell).name

    if shell_name in ("bash", "sh"):
        # bash --rcfile para cargar activate y mantener prompt (venv)
        rcfile = VENV_DIR / ".psyai_activate_rc"
        rcfile.write_text(f"source '{act}'\n")
        try:
            return subprocess.call(
                [shell, "--rcfile", str(rcfile), "-i"], cwd=PROJECT_ROOT
            )
        finally:
            rcfile.unlink(missing_ok=True)

    if shell_name == "zsh":
        # zsh: source activate y exec zsh interactivo
        return subprocess.call(
            [shell, "-i", "-c", f"source '{act}' && exec {shell} -i"],
            cwd=PROJECT_ROOT,
        )

    if shell_name == "fish":
        fish_act = scripts / "activate.fish"
        if fish_act.exists():
            return subprocess.call(
                [shell, "-C", f"source '{fish_act}'", "-i"], cwd=PROJECT_ROOT
            )

    # Fallback genérico: setear VIRTUAL_ENV + PATH y lanzar shell
    info(f"Shell no reconocido ({shell_name}), activando vía variables de entorno")
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(VENV_DIR.resolve())
    env["PATH"] = f"{scripts.resolve()}{os.pathsep}{env.get('PATH', '')}"
    env.pop("PYTHONHOME", None)
    return subprocess.call([shell, "-i"], env=env, cwd=PROJECT_ROOT)


# ── Programa principal ───────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Instalador PsyAI Connect: crea venv, instala deps y abre shell activado",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--no-shell",
        action="store_true",
        help="Instala dependencias pero no abre la terminal activada",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Borra y recrea el entorno virtual desde cero",
    )
    args = parser.parse_args()

    banner()

    if not check_python_version():
        return 1
    if not check_requirements():
        return 1

    if not create_venv(args.recreate):
        return 1
    if not upgrade_pip():
        return 1
    if not install_deps():
        return 1

    verify_install()

    # ── Próximos pasos ──────────────────────────────────────────────────────
    header("[OK] Instalación completada")
    print(
        "\n  Próximos pasos:\n"
        "  1. Copia y configura variables de entorno:\n"
        "       cp .env.example .env   # y edita .env\n"
        "  2. Ejecuta migraciones:\n"
        "       python manage.py migrate\n"
        "  3. (Opcional) Crea superusuario:\n"
        "       python manage.py createsuperuser\n"
        "  4. Levanta el servidor:\n"
        "       python manage.py runserver\n"
    )

    if args.no_shell:
        act = activate_script()
        print(
            "\n  Para activar el entorno manualmente:\n"
            f"    {act if IS_WINDOWS else f'source {act}'}\n"
        )
        return 0

    return open_activated_shell()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n  Instalación cancelada por el usuario.")
        sys.exit(130)