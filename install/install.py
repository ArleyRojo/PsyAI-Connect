#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
══════════════════════════════════════════════════════════════════════════════════
PsyAI Connect — Instalador de entorno virtual y dependencias
══════════════════════════════════════════════════════════════════════════════════

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
══════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


class Installer:
    """Instalador de entorno virtual y dependencias para PsyAI Connect."""

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    VENV_DIR = PROJECT_ROOT / "venv"
    REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
    ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
    ENV_FILE = PROJECT_ROOT / ".env"

    IS_WINDOWS = os.name == "nt"
    MIN_PYTHON = (3, 10)

    # ── Utilidades de consola ────────────────────────────────────────────────
    def banner(self) -> None:
        line = "=" * 72
        print(f"\n{line}")
        print("  PsyAI Connect - Instalador automatico")
        print(line)

    def step(self, msg: str) -> None:
        print(f"  > {msg}")

    def ok(self, msg: str) -> None:
        print(f"  [OK] {msg}")

    def warn(self, msg: str) -> None:
        print(f"  [WARN] {msg}", file=sys.stderr)

    def error(self, msg: str) -> None:
        print(f"\n  [ERROR] {msg}\n", file=sys.stderr)

    def info(self, msg: str) -> None:
        print(f"  -> {msg}")

    def header(self, title: str) -> None:
        line = "=" * 72
        print(f"\n{line}")
        print(f"  {title}")
        print(line)

    # ── Helpers de rutas del venv ────────────────────────────────────────────
    def venv_scripts_dir(self) -> Path:
        return self.VENV_DIR / ("Scripts" if self.IS_WINDOWS else "bin")

    def venv_python(self) -> Path:
        name = "python.exe" if self.IS_WINDOWS else "python"
        return self.venv_scripts_dir() / name

    def venv_pip(self) -> Path:
        name = "pip.exe" if self.IS_WINDOWS else "pip"
        return self.venv_scripts_dir() / name

    def activate_script(self) -> Path:
        if self.IS_WINDOWS:
            return self.venv_scripts_dir() / "activate.bat"
        return self.venv_scripts_dir() / "activate"

    # ── Comprobaciones previas ───────────────────────────────────────────────
    def check_python_version(self) -> bool:
        if sys.version_info < self.MIN_PYTHON:
            self.error(
                f"Se requiere Python {self.MIN_PYTHON[0]}.{self.MIN_PYTHON[1]}+ "
                f"(actual: {sys.version_info.major}.{sys.version_info.minor})"
            )
            return False
        self.ok(f"Python {sys.version_info.major}.{sys.version_info.minor} detectado")
        return True

    def check_requirements(self) -> bool:
        if not self.REQUIREMENTS.exists():
            self.error(f"No se encontró {self.REQUIREMENTS}")
            return False
        self.ok("requirements.txt encontrado")
        return True

    # ── Crear / recrear entorno virtual ──────────────────────────────────────
    def create_venv(self, recreate: bool) -> bool:
        if self.VENV_DIR.exists():
            if recreate:
                self.step("Borrando entorno virtual anterior...")
                shutil.rmtree(self.VENV_DIR)
            else:
                self.ok(f"Entorno virtual ya existe en {self.VENV_DIR}")
                return True

        self.step(f"Creando entorno virtual en {self.VENV_DIR}...")
        result = subprocess.run([sys.executable, "-m", "venv", str(self.VENV_DIR)])
        if result.returncode != 0:
            self.error("No se pudo crear el entorno virtual")
            return False
        self.ok("Entorno virtual creado")
        return True

    # ── Instalar dependencias ────────────────────────────────────────────────
    def upgrade_pip(self) -> bool:
        self.step("Actualizando pip...")
        result = subprocess.run(
            [str(self.venv_python()), "-m", "pip", "install", "--upgrade", "pip", "--quiet"]
        )
        if result.returncode != 0:
            self.warn("No se pudo actualizar pip (continuando)")
            return False
        self.ok("pip actualizado")
        return True

    def install_deps(self) -> bool:
        self.step("Instalando dependencias desde requirements.txt...")
        result = subprocess.run(
            [str(self.venv_python()), "-m", "pip", "install", "-r", str(self.REQUIREMENTS)]
        )
        if result.returncode != 0:
            self.error(
                "Falló la instalación de dependencias.\n"
                "  • En Windows: mysqlclient puede requerir wheels o "
                "Microsoft Visual C++ Build Tools.\n"
                "  • En Linux: instale pkg-config y default-libmysqlclient-dev."
            )
            return False
        self.ok("Dependencias instaladas")
        return True

    def verify_install(self) -> None:
        self.step("Verificando instalación...")
        result = subprocess.run(
            [str(self.venv_python()), "-m", "pip", "check"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            self.ok("pip check: sin conflictos")
        else:
            self.warn(f"pip check reportó:\n{result.stdout.strip()}")

    # ── Abrir terminal con el venv activado ──────────────────────────────────
    def open_activated_shell(self) -> int:
        """Lanza una shell interactiva con el entorno virtual activado."""
        scripts = self.venv_scripts_dir()
        act = self.activate_script()

        self.header("Abriendo terminal con entorno activado")

        if self.IS_WINDOWS:
            # Preferir PowerShell si estamos en él (PSModulePath existe)
            if os.environ.get("PSModulePath"):
                ps_activate = scripts / "Activate.ps1"
                pwsh = shutil.which("pwsh") or shutil.which("powershell")
                if pwsh and ps_activate.exists():
                    self.info("Detectado PowerShell → usando Activate.ps1")
                    return subprocess.call(
                        [
                            pwsh,
                            "-NoExit",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-Command",
                            f"& '{ps_activate}'",
                        ],
                        cwd=self.PROJECT_ROOT,
                    )
            # Fallback: cmd.exe clásico
            comspec = os.environ.get("COMSPEC", "cmd.exe")
            self.info("Usando cmd.exe → activate.bat")
            return subprocess.call(
                [comspec, "/k", f'call "{act}"'],
                cwd=self.PROJECT_ROOT,
            )

        # ── Unix (Linux/macOS) ───────────────────────────────────────────────
        shell = os.environ.get("SHELL", "/bin/bash")
        shell_name = Path(shell).name

        if shell_name in ("bash", "sh"):
            # bash --rcfile para cargar activate y mantener prompt (venv)
            rcfile = self.VENV_DIR / ".psyai_activate_rc"
            rcfile.write_text(f"source '{act}'\n")
            try:
                return subprocess.call(
                    [shell, "--rcfile", str(rcfile), "-i"], cwd=self.PROJECT_ROOT
                )
            finally:
                rcfile.unlink(missing_ok=True)

        if shell_name == "zsh":
            # zsh: source activate y exec zsh interactivo
            return subprocess.call(
                [shell, "-i", "-c", f"source '{act}' && exec {shell} -i"],
                cwd=self.PROJECT_ROOT,
            )

        if shell_name == "fish":
            fish_act = scripts / "activate.fish"
            if fish_act.exists():
                return subprocess.call(
                    [shell, "-C", f"source '{fish_act}'", "-i"], cwd=self.PROJECT_ROOT
                )

        # Fallback genérico: setear VIRTUAL_ENV + PATH y lanzar shell
        self.info(f"Shell no reconocido ({shell_name}), activando vía variables de entorno")
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(self.VENV_DIR.resolve())
        env["PATH"] = f"{scripts.resolve()}{os.pathsep}{env.get('PATH', '')}"
        env.pop("PYTHONHOME", None)
        return subprocess.call([shell, "-i"], env=env, cwd=self.PROJECT_ROOT)

    def run(self, no_shell: bool = False, recreate: bool = False) -> int:
        """Ejecuta el flujo completo de instalación.

        Args:
            no_shell: Instala dependencias pero no abre la terminal activada.
            recreate: Borra y recrea el entorno virtual desde cero.

        Returns:
            Código de salida del proceso.
        """
        self.banner()

        if not self.check_python_version():
            return 1
        if not self.check_requirements():
            return 1

        if not self.create_venv(recreate):
            return 1
        if not self.upgrade_pip():
            return 1
        if not self.install_deps():
            return 1

        self.verify_install()

        # ── Próximos pasos ──────────────────────────────────────────────────
        self.header("[OK] Instalación completada")
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

        if no_shell:
            act = self.activate_script()
            print(
                "\n  Para activar el entorno manualmente:\n"
                f"    {act if self.IS_WINDOWS else f'source {act}'}\n"
            )
            return 0

        return self.open_activated_shell()


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

    installer = Installer()
    try:
        return installer.run(no_shell=args.no_shell, recreate=args.recreate)
    except KeyboardInterrupt:
        print("\n\n  Instalación cancelada por el usuario.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
