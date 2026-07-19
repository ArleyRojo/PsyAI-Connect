<div align="center">

# 🧠 PsyAI Connect

**Plataforma web de gestión para consultorios de psicología, potenciada con IA**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8+-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-219%20passing-brightgreen)](#-testing)
[![Gemini](https://img.shields.io/badge/IA-Google%20Gemini-8E75B2?logo=googlegemini&logoColor=white)](https://aistudio.google.com/)
[![Licencia](https://img.shields.io/badge/uso-educativo-lightgrey)](#-licencia)

</div>

---

**PsyAI Connect** conecta pacientes con profesionales de salud mental en un solo lugar: agendamiento de citas, seguimiento terapéutico, mensajería en tiempo real, facturación y un chatbot de triaje psicológico impulsado por la API de Google Gemini.

## 📑 Tabla de contenidos

- [Objetivo](#-objetivo)
- [Tecnologías](#-tecnologías)
- [Arquitectura](#-arquitectura)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Roles de usuario](#-roles-de-usuario)
- [Instalación](#-instalación)
- [Variables de entorno](#-variables-de-entorno)
- [Testing](#-testing)
- [Características principales](#-características-principales)
- [Seguridad](#-seguridad)
- [Licencia](#-licencia)

---

## 🎯 Objetivo

Digitalizar y centralizar la operación de un consultorio o red de psicólogos, ofreciendo:

- 🧑‍⚕️ Un portal para **pacientes**: agendar citas, ver su evolución, chatear con su terapeuta, consultar el chatbot de apoyo y revisar sus facturas.
- 👩‍⚕️ Un portal para **profesionales**: gestionar su agenda, revisar el historial de sus pacientes y generar reportes.
- 🛠️ Un panel de **administración**: métricas en tiempo real, gestión de usuarios y roles, logs del sistema y configuración del chatbot de IA.

---

## 🧩 Tecnologías

### Backend

| Tecnología | Uso |
|---|---|
| **Python 3.10+** | Lenguaje principal |
| **Django 5** | Framework web |
| **Django REST Framework** | APIs REST |
| **MySQL 8+** | Base de datos relacional |
| **mysqlclient** | Driver de conexión a MySQL |
| **Waitress** | Servidor WSGI para producción |
| **python-dotenv** | Gestión de variables de entorno |
| **psutil** | Métricas del sistema (CPU, RAM, disco) |
| **bcrypt** | Hash seguro de contraseñas |
| **Brevo** | Envío de correos transaccionales |
| **Wompi** | Pasarela de pago para facturación |

### Inteligencia artificial

| Tecnología | Uso |
|---|---|
| **Google Gemini API** | Chatbot de triaje psicológico para pacientes |

La integración con Gemini soporta **rotación automática de API keys** (`GEMINI_API_KEYS`) para distribuir cuota entre múltiples proyectos de Google AI Studio, y un nivel de "pensamiento" configurable (`GEMINI_THINKING_LEVEL`) desde el panel de administración.

### Frontend

| Tecnología | Uso |
|---|---|
| **HTML / Django Templates / Bootstrap 5.0.2** | Plantillas del servidor |
| **CSS personalizado** | Estilos por módulo, tema (claro/oscuro) y responsividad |
| **JavaScript vanilla** | Lógica de UI por módulo (sin frameworks) |
| **SSE (Server-Sent Events)** | Actualizaciones en tiempo real en el panel admin y el chat |

Los CDNs (Google Fonts, Bootstrap, Font Awesome) y el CSS/JS core se cargan desde un único `<head>` compartido (`templates/base/partials/head.html`), incluido en todas las páginas — cambiar una versión de librería se hace en un solo archivo.

### Testing y DevOps

| Tecnología | Uso |
|---|---|
| **pytest + pytest-django** | Unit tests e integration tests |
| **pytest-cov** | Cobertura de código |
| **Docker + Docker Compose** | Containerización y desarrollo reproducible |
| SQLite en memoria | Base de datos de test (aislada de MySQL, ver `conftest.py`) |

---

## 🏗️ Arquitectura

El proyecto sigue una **arquitectura en capas** (Repository + Service Layer), replicada de forma consistente en cada app de `apps/`:

```
Vistas (views.py) → Servicios (services.py) → Repositorios (repositories.py) → MySQL
```

- **`views.py`** — endpoints REST y de página; delegan toda la lógica a la capa de servicios.
- **`services.py`** — lógica de negocio y validaciones. Cada servicio instancia su repositorio correspondiente.
- **`repositories.py`** — encapsula todas las consultas a la base de datos.
- **`models.py`** — entidades de dominio (Django ORM).
- **`admin.py`** — registro de modelos en el admin nativo de Django.
- **`apps/core/`** — utilidades transversales: excepciones, **permisos centralizados** (`core/permissions.py`), middlewares, autenticación y correo.

Esta separación mantiene las vistas delgadas y hace que la lógica de negocio sea fácil de testear de forma aislada, mockeando el repositorio correspondiente — es la base de los 219 tests del proyecto.

---

## 📁 Estructura del proyecto

```
PsyAI-Connect/
│
├── manage.py
├── requirements.txt
├── setup_install.py             # Instalador automático (venv + .env)
├── pytest.ini                   # Configuración de pytest
├── conftest.py                  # Fixtures globales (SQLite override)
├── .dockerignore
├── .env.example
├── .gitignore
│
├── docker/
│   ├── Dockerfile               # Multi-stage: dev / prod
│   ├── docker-compose.yml       # Desarrollo: app + MySQL
│   ├── docker-compose.prod.yml  # Producción (override)
│   └── entrypoint.sh            # Espera MySQL, migra, arranca server
│
├── config/
│   ├── asgi.py
│   ├── urls.py
│   ├── wsgi.py
│   └── settings/
│       ├── base.py              # Configuración común
│       ├── dev.py               # Desarrollo (DEBUG=True)
│       └── prod.py              # Producción (DEBUG=False, seguridad)
│
├── apps/
│   ├── admin_panel/             # Panel de administración
│   ├── authentication/          # Registro, login, recuperación
│   ├── billing/                 # Facturación y pasarela de pago
│   ├── chatbot/                 # Chatbot IA con Gemini
│   ├── core/                    # Permisos, middlewares, utilidades
│   ├── documents/                # Documentos clínicos
│   ├── patients/                 # Portal de pacientes
│   ├── professionals/            # Portal de profesionales
│   └── scheduling/               # Agendamiento de citas
│       ├── models.py
│       ├── repositories.py
│       ├── services.py
│       ├── views.py
│       ├── admin.py
│       ├── migrations/
│       └── tests/
│           ├── conftest.py
│           └── test_services.py
│
├── static/
│   ├── css/
│   │   ├── base/ layout/ themes/ pages/ components/
│   ├── js/
│   ├── img/
│   ├── responsive/
│   └── uploads/documentos/      # Documentos subidos por usuarios
│
├── templates/
│   ├── base/
│   │   └── partials/            # head.html y scripts.html compartidos
│   ├── admin/
│   ├── auth/
│   ├── legal/
│   ├── patient/
│   └── professional/
│
└── tests/
    └── test_integration.py      # Integration tests (Django test client)
```

> Cada una de las 8 apps de negocio replica la misma estructura interna mostrada arriba para `scheduling`, incluyendo su propia carpeta `tests/`.

---

## 👥 Roles de usuario

| Rol | Descripción |
|---|---|
| 🧑‍⚕️ **Paciente** | Agenda citas, consulta su evolución, usa el chatbot de IA, chatea con su terapeuta y revisa sus facturas |
| 👩‍⚕️ **Profesional** | Gestiona su agenda, revisa pacientes asignados y genera reportes |
| 🛠️ **Administrador** | Panel completo: usuarios, roles, logs, métricas del servidor y configuración del chatbot |

---

## 🚀 Instalación

### Requisitos previos

- Python 3.10+
- MySQL 8+ (o Docker)
- Una API key de [Google AI Studio](https://aistudio.google.com/) para el chatbot

### Opción 1: Docker (recomendado)

```bash
# 1. Clonar el repositorio
git clone https://github.com/ArleyRojo/PsyAI-Connect.git
cd PsyAI-Connect

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con SECRET_KEY y credenciales

# 3. Levantar los contenedores (app + MySQL)
docker compose -f docker/docker-compose.yml up

# El servidor estará disponible en http://localhost:8000
# MySQL accesible en localhost:3307
```

El `docker/entrypoint.sh` se encarga automáticamente de:
- Esperar a que MySQL esté listo
- Ejecutar las migraciones
- Crear un superuser de prueba **(solo para desarrollo local — ver [Seguridad](#-seguridad))**
- Arrancar el servidor de desarrollo

#### Comandos útiles con Docker

```bash
docker compose -f docker/docker-compose.yml up -d              # Arrancar en background
docker compose -f docker/docker-compose.yml logs -f app        # Ver logs de la app
docker compose -f docker/docker-compose.yml exec app bash      # Shell dentro del contenedor
docker compose -f docker/docker-compose.yml down               # Detener contenedores
docker compose -f docker/docker-compose.yml down -v             # Detener y eliminar volúmenes
```

#### Producción con Docker

```bash
# Usar el override de producción (waitress, sin hot-reload)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
```

### Opción 2: Instalación manual

```bash
# 1. Clonar el repositorio
git clone https://github.com/ArleyRojo/PsyAI-Connect.git
cd PsyAI-Connect

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de MySQL y SECRET_KEY

# 5. Crear la base de datos
mysql -u root -p -e "CREATE DATABASE psyai_connect CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 6. Ejecutar migraciones
python manage.py migrate

# 7. Crear superuser (opcional)
python manage.py createsuperuser

# 8. Iniciar el servidor
python manage.py runserver
```

El servidor estará disponible en `http://127.0.0.1:8000`.

### Instalación asistida (opcional)

```bash
python setup_install.py
```

Automatiza la creación del entorno virtual, la instalación de dependencias y la generación del `.env`. Revisa el `.env` generado antes de usarlo — no debe contener API keys, contraseñas ni correos reales de ejemplo.

---

## 🔑 Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `SECRET_KEY` | Clave secreta para firmar sesiones Django | *(sin default seguro — obligatoria en producción)* |
| `PORT` | Puerto del servidor | `8000` |
| `DB_HOST` | Host de MySQL | `localhost` |
| `DB_PORT` | Puerto de MySQL | `3306` |
| `DB_USER` | Usuario de MySQL | `root` |
| `DB_PASSWORD` | Contraseña de MySQL | `root` |
| `DB_NAME` | Nombre de la base de datos | `psyai_connect` |
| `DB_ROOT_PASSWORD` | Password root de MySQL (solo Docker) | `rootpass` |
| `GEMINI_MODEL` | Modelo de Gemini | `gemini-3.1-flash-lite` |
| `GEMINI_THINKING_LEVEL` | Nivel de razonamiento (`minimal`, `low`, `medium`, `high`) | `low` |
| `GEMINI_API_KEY` | API key de Google Gemini (una sola) | Para chatbot |
| `GEMINI_API_KEYS` | API keys separadas por coma (rotación automática) | Para chatbot |
| `EMAIL_HOST` | Servidor SMTP | `smtp.gmail.com` |
| `EMAIL_PORT` | Puerto SMTP | `587` |
| `EMAIL_USE_TLS` | Usar TLS | `True` |
| `EMAIL_HOST_USER` | Usuario SMTP | — |
| `EMAIL_HOST_PASSWORD` | Contraseña SMTP | — |
| `DEFAULT_FROM_EMAIL` | Dirección de envío | — |
| `LOGIN_RATE_LIMIT` | Límite para login | `60 per minute` |
| `REGISTER_RATE_LIMIT` | Límite para registro | `20 per minute` |
| `PASSWORD_RECOVERY_RATE_LIMIT` | Límite para recuperación | `10 per minute` |

Consulta [`.env.example`](./.env.example) para la plantilla completa.

### Variables de entorno para Docker

Las siguientes ya tienen defaults en `docker-compose.yml` y coinciden con `.env.example`:

```bash
DB_NAME=psyai_connect
DB_USER=psyai
DB_PASSWORD=psyai_pass
DB_HOST=db              # nombre del servicio MySQL en Docker
DB_PORT=3306
DB_ROOT_PASSWORD=rootpass
```

---

## ✅ Testing

El proyecto tiene **219 tests** (199 unitarios + 20 de integración) con **pytest + pytest-django**.

```bash
# Todos los tests
python -m pytest

# Unit tests solamente (199 tests, usan SQLite en memoria, no requieren MySQL)
python -m pytest apps/

# Integration tests (20 tests, requieren la app completa contra MySQL)
python -m pytest tests/

# Con cobertura
python -m pytest --cov=apps --cov-report=term-missing

# Verbose
python -m pytest -v
```

### Tests dentro de Docker

```bash
# Unit tests (no necesitan MySQL)
docker compose -f docker/docker-compose.yml exec app python -m pytest apps/ -q

# Todos los tests
docker compose -f docker/docker-compose.yml exec app python -m pytest -q
```

### Estructura de tests

Cada app tiene su carpeta `tests/` con:

- `conftest.py` — fixtures locales (mocks de repositorios, instancias de servicios)
- `test_services.py` — tests unitarios de la capa de servicios

Los tests usan **mocking de repositorios** para aislar la lógica de negocio de la base de datos. El `conftest.py` de la raíz fuerza SQLite en memoria de forma automática (`autouse`) para todos los unit tests, por lo que corren rápido y sin depender de MySQL ni de credenciales configuradas.

Los **integration tests** (`tests/test_integration.py`) usan el Django test client para hacer requests HTTP reales a los endpoints, y sí requieren la base de datos configurada.

---

## ✨ Características principales

- **Autenticación completa**: registro, login, recuperación de contraseña por correo y reset con token seguro.
- **Chatbot de triaje con IA**: integrado con Google Gemini, con prompt del sistema configurable desde el panel admin, caché de configuración, detección de palabras de riesgo y rotación automática de API keys.
- **Chat en tiempo real**: mensajería directa entre paciente y profesional usando Server-Sent Events (SSE).
- **Gestión de citas**: creación, visualización y seguimiento de citas por parte de pacientes y profesionales.
- **Historia clínica**: diagnósticos y documentos clínicos adjuntos, visibles para el paciente y gestionados por el profesional.
- **Evolución del paciente**: seguimiento del progreso terapéutico con entradas diarias.
- **Facturación**: creación de facturas, integración con pasarela de pago **Wompi**, gestión de estados y anulaciones.
- **Telemetría en vivo**: el panel admin muestra en tiempo real el uso de CPU, RAM, disco, número de peticiones, endpoints más usados y eventos de seguridad.
- **Sistema de temas**: soporte para modo claro y oscuro persistido por usuario, con paleta de marca centralizada en variables CSS.
- **Diseño responsivo**: CSS adaptativo para móvil, tablet y escritorio por cada sección.
- **Rate limiting**: protección de endpoints sensibles contra abuso, con configuración diferenciada por entorno.
- **CSRF**: protección contra Cross-Site Request Forgery habilitada por defecto en todos los formularios.
- **Admin nativo de Django**: los modelos de cada app están registrados en `admin.py` para inspección y gestión rápida desde `/admin`.
- **Docker**: containerización lista para desarrollo y producción con hot-reload, MySQL persistente y migraciones automáticas. Archivos organizados en `docker/`.
- **219 tests**: unit tests e integration tests cubriendo las capas de servicios y endpoints HTTP.

---

## 🔒 Seguridad

Este proyecto maneja **datos sensibles de salud mental** (historia clínica, diagnósticos, evolución terapéutica). Medidas ya implementadas:

- **CSRF**: protección habilitada por defecto en todos los formularios.
- **Rate limiting**: endpoints de autenticación protegidos contra abuso.
- **HSTS**: habilitado en producción (1 año, incluye subdominios).
- **SSL redirect**: forzado en producción.
- **Cookies seguras**: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `CSRF_COOKIE_HTTPONLY` en producción.
- **Validación de `SECRET_KEY`**: en producción, el servidor se niega a arrancar si `SECRET_KEY` no está configurada o usa el valor inseguro por defecto.
- **Content-Type nosniff**: `X-Content-Type-Options: nosniff` habilitado.
- **X-Frame-Options**: `DENY` para prevenir clickjacking.
- **Permisos centralizados**: control de acceso por rol gestionado desde `apps/core/permissions.py`, no repetido en cada vista.

A tener en cuenta:

- El **superuser de prueba** que crea `docker/entrypoint.sh` automáticamente está pensado **solo para desarrollo local**. No uses ese mismo flujo de arranque automático en una instancia expuesta públicamente sin cambiar esa credencial o desactivar su creación.
- **Nunca subas `.env` al repositorio.** Usa siempre `.env.example` como plantilla y mantén `.env` en `.gitignore`.
- **No hardcodees credenciales en el código**, incluyendo scripts auxiliares como `setup_install.py`. Si alguna API key, contraseña o correo personal quedó escrito directamente en un script, revócala/rótala y muévela a variables de entorno.
- Si el repositorio llegó a tener credenciales reales en algún commit anterior, cambiarlas en el archivo actual **no es suficiente**: siguen visibles en el historial de Git. Hay que rotarlas y, si aplica, limpiar el historial (por ejemplo con `git filter-repo`).

---

## 📄 Licencia

Este proyecto es de uso educativo/interno. Revisa el repositorio para más detalles sobre su licencia.
