import os
import subprocess
import secrets


def print_separator(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def run_command(cmd, error_msg):
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"\n[ERROR] {error_msg}")
        input("Presiona Enter para salir...")
        exit(1)
    return result


# ── 1. Verificar Python ───────────────────────────────────────────────
print_separator("PsyAI Connect - Instalacion")

python_cmd = "python"
try:
    subprocess.run(f"{python_cmd} --version", shell=True, capture_output=True, check=True)
except subprocess.CalledProcessError:
    python_cmd = "py"
    try:
        subprocess.run(f"{python_cmd} --version", shell=True, capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("[ERROR] Python no encontrado.")
        print("Descargalo en: https://www.python.org/downloads/")
        print('Marca "Add Python to PATH" al instalar.')
        input("Presiona Enter para salir...")
        exit(1)

print(f"  [OK] Python detectado ({python_cmd}).\n")


# ── 2. Verificar requirements.txt ─────────────────────────────────────
print_separator("Verificando dependencias")

if not os.path.exists("requirements.txt"):
    print("[ERROR] No se encuentra requirements.txt.")
    print("Asegurate de que el archivo este en el directorio actual.")
    input("Presiona Enter para salir...")
    exit(1)

print("  [OK] requirements.txt encontrado.\n")


# ── 3. Crear entorno virtual ──────────────────────────────────────────
print_separator("Entorno virtual")

if not os.path.exists("venv"):
    print("Creando entorno virtual...")
    run_command(f"{python_cmd} -m venv venv", "No se pudo crear el entorno virtual.")
    print("  [OK] Entorno virtual creado.\n")
else:
    print("  [OK] venv ya existe.\n")


# ── 4. Instalar dependencias en venv ───────────────────────────────────
print_separator("Instalando dependencias (venv)")

venv_python = os.path.join("venv", "Scripts", "python.exe")
run_command(
    f"{venv_python} -m pip install --upgrade pip -q",
    "No se pudo actualizar pip."
)
run_command(
    f"{venv_python} -m pip install -r requirements.txt",
    "Fallo al instalar dependencias en venv."
)
print("  [OK] Dependencias instaladas en venv.\n")


# ── 5. Instalar dependencias globalmente ───────────────────────────────
print_separator("Instalando dependencias (global)")

global_result = subprocess.run(
    f"{python_cmd} -m pip install -r requirements.txt",
    shell=True
)
if global_result.returncode == 0:
    print("  [OK] Dependencias instaladas globalmente.\n")
else:
    print("  [WARNING] No se pudieron instalar las dependencias globalmente.")
    print("           Puedes ignorar esto si solo usas el entorno virtual.\n")


# ── 6. Crear .env si no existe ─────────────────────────────────────────
print_separator("Archivo de configuracion (.env)")

ENV_FILE = ".env"
if not os.path.exists(ENV_FILE):
    secret_key = secrets.token_hex(32)
    print("Generando .env con SECRET_KEY unica...")
    with open(ENV_FILE, "w") as f:
        f.write("# --- Flask ---------------------------------------------------\n")
        f.write(f"SECRET_KEY={secret_key}\n")
        f.write("\n")
        f.write("FLASK_ENV=development\n")
        f.write("\n")
        f.write("# --- Base de datos MySQL (XAMPP) ----------------------------\n")
        f.write("DB_HOST=localhost\n")
        f.write("DB_PORT=3306\n")
        f.write("DB_USER=root\n")
        f.write("DB_PASSWORD=root\n")
        f.write("DB_NAME=psyai_connect\n")
        f.write("\n")
        f.write("# --- Pool de conexiones --------------------------------------\n")
        f.write("DB_POOL_NAME=psyai_pool\n")
        f.write("DB_POOL_SIZE=5\n")
        f.write("DB_POOL_RESET_SESSION=true\n")
        f.write("\n")
        f.write("# --- Gemini AI -----------------------------------------------\n")
        f.write("GEMINI_API_KEY=YOUR_GEMINI_API_KEY\n")
        f.write("GEMINI_MODEL=gemini-2.5-flash\n")
        f.write("\n")
        f.write("# --- Logs ----------------------------------------------------\n")
        f.write("LOG_LEVEL=INFO\n")
        f.write("LOG_FORMAT=werkzeug\n")
    print("  [OK] .env creado.\n")
else:
    print("  [OK] .env ya existe.\n")


# ── 7. Finalizar ──────────────────────────────────────────────────────
print_separator("Instalacion completada")

print("Instalacion completada correctamente.")
print("Edita el archivo .env y agrega tu Gemini API key.")
print()
input("Presiona Enter para salir...")
