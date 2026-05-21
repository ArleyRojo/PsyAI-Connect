import sys
import os
import subprocess
import secrets


def install_package(package):
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'show', package],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"\u26a0\ufe0f {package} ya estaba instalado")
    else:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', package],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print(f"\u2705 {package} instalado")


def main():
    print("Iniciando configuraci\u00f3n de PsyAI Connect...\n")

    # 1. Instalar dependencias
    packages = [
        'python-dotenv',
        'bcrypt',
        'requests',
    ]
    for pkg in packages:
        install_package(pkg)

    print()

    # 2. Configurar .env y SECRET_KEY
    from dotenv import load_dotenv, set_key

    if not os.path.exists('.env'):
        with open('.env', 'a'):
            pass

    load_dotenv()

    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        new_secret = secrets.token_hex(32)
        set_key('.env', 'SECRET_KEY', new_secret)
        print("\u2705 SECRET_KEY configurado.")
    else:
        print("\u2705 SECRET_KEY ya estaba configurado.")

    # 3. Resumen final
    print()
    print("\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557")
    print("\u2551   PsyAI Connect \u2014 Setup completado  \u2551")
    print("\u2551   Corre: python run.py              \u2551")
    print("\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d")


if __name__ == '__main__':
    main()
