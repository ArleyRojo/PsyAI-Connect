@echo off
REM ============================================================
REM PsyAI Connect - Script de instalación para Windows
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   PsyAI Connect - Configuración del entorno
REM echo   Fecha: %date% %time%
echo ============================================================
echo.

REM ------------------------------------------------------------
REM Paso 1: Verificar que Python esté instalado
REM ------------------------------------------------------------
echo [1/4] Verificando instalación de Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo.
        echo   [ERROR] Python no está instalado en este equipo.
        echo.
        echo   Descarga e instala Python 3.8 o superior desde:
        echo   https://www.python.org/downloads/
        echo.
        echo   IMPORTANTE: Marca la opción "Add Python to PATH"
        echo   durante la instalación.
        echo.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

%PYTHON_CMD% --version
for /f "tokens=2" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set PYM=%%a
    set PYN=%%b
)
if !PYM! lss 3 (
    echo.
    echo   [ERROR] Se requiere Python 3.8 o superior.
    echo   Versión detectada: !PYVER!
    echo.
    pause
    exit /b 1
)
if !PYM! equ 3 if !PYN! lss 8 (
    echo.
    echo   [ERROR] Se requiere Python 3.8 o superior.
    echo   Versión detectada: !PYVER!
    echo.
    pause
    exit /b 1
)
echo   ✓ Python detectado (!PYVER!)

REM ------------------------------------------------------------
REM Paso 2: Crear entorno virtual si no existe
REM ------------------------------------------------------------
echo.
echo [2/4] Configurando entorno virtual...

if not exist "venv\" (
    echo   Creando entorno virtual 'venv'...
    %PYTHON_CMD% -m venv venv
    if !errorlevel! neq 0 (
        echo.
        echo   [ERROR] No se pudo crear el entorno virtual.
        echo   Asegúrate de tener instalado el módulo 'venv'.
        echo.
        pause
        exit /b 1
    )
    echo   ✓ Entorno virtual creado
) else (
    echo   ✓ Entorno virtual ya existe
)

REM ------------------------------------------------------------
REM Paso 3: Activar entorno virtual
REM ------------------------------------------------------------
echo.
echo [3/4] Activando entorno virtual...

call venv\Scripts\activate
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] No se pudo activar el entorno virtual.
    echo   Intenta activarlo manualmente con: venv\Scripts\activate
    echo.
    pause
    exit /b 1
)
echo   ✓ Entorno virtual activado

REM ------------------------------------------------------------
REM Paso 4: Instalar dependencias
REM ------------------------------------------------------------
echo.
echo [4/4] Instalando dependencias...

if not exist "requirements.txt" (
    echo.
    echo   [ERROR] No se encontró el archivo 'requirements.txt'
    echo   Asegúrate de ejecutar este script desde la raíz del proyecto.
    echo.
    pause
    exit /b 1
)

pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] No se pudieron instalar las dependencias.
    echo.
    pause
    exit /b 1
)
echo   ✓ Dependencias instaladas correctamente

REM ------------------------------------------------------------
REM ¡Éxito!
REM ------------------------------------------------------------
echo.
echo ============================================================
echo   ¡Instalación completada con éxito! ✓
echo ============================================================
echo.
echo   Para iniciar el proyecto, ejecuta los siguientes comandos:
echo.
echo     1. Activar el entorno virtual:
echo        venv\Scripts\activate
echo.
echo     2. Iniciar el servidor:
echo        python run.py
echo.
echo   El servidor estará disponible en: http://127.0.0.1:5000
echo.
echo   Presiona cualquier tecla para cerrar...
echo ============================================================

endlocal
pause >nul