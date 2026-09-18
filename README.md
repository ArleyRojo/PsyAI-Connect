# PsyAI Connect

**PsyAI Connect** es una plataforma web de gestión para consultorios de psicología que integra inteligencia artificial. Conecta pacientes con profesionales de salud mental, permitiendo agendar citas, llevar seguimiento terapéutico, chatear en tiempo real y acceder a un chatbot de triaje psicológico impulsado por la API de Google Gemini.

---

## Objetivo

Digitalizar y centralizar la operación de un consultorio o red de psicólogos, ofreciendo:

- Un portal para **pacientes** donde puedan agendar citas, ver su evolución, chatear con su terapeuta y consultar un chatbot de apoyo.
- Un portal para **profesionales** donde gestionen su agenda, revisen el historial de sus pacientes y generen reportes.
- Un panel de **administración** con métricas en tiempo real, gestión de usuarios, roles, logs del sistema y configuración del chatbot de IA.

---

## Tecnologías

### Backend
| Tecnología | Uso |
|---|---|
| **Python 3** | Lenguaje principal |
| **Django 5** | Framework web |
| **Django REST Framework** | APIs REST |
| **MySQL** | Base de datos relacional |
| **mysqlclient** | Driver de conexión a MySQL |
| **Waitress** | Servidor WSGI para producción |
| **python-dotenv** | Gestión de variables de entorno |
| **psutil** | Métricas del sistema (CPU, RAM, disco) |
| **bcrypt** | Hash seguro de contraseñas |
| **Brevo** | Envío de correos transaccionales |

### Inteligencia Artificial
| Tecnología | Uso |
|---|---|
| **Google Gemini API** | Chatbot de triaje psicológico para pacientes |

La integración con Gemini soporta **rotación automática de API keys** para distribuir cuota entre múltiples proyectos de Google AI Studio.

### Frontend
| Tecnología | Uso |
|---|---|
| **HTML / Django Templates / Bootstrap 5.0.2** | Plantillas del servidor |
| **CSS personalizado** | Estilos por módulo, tema y responsividad |
| **JavaScript vanilla** | Lógica de UI por módulo (sin frameworks) |
| **SSE (Server-Sent Events)** | Actualizaciones en tiempo real en el panel admin y el chat |

### Testing y DevOps
| Tecnología | Uso |
|---|---|
| **pytest + pytest-django** | Unit tests e integration tests |
| **pytest-cov** | Cobertura de código |
| **Docker + Docker Compose** | Containerización y desarrollo reproducible |

---

## Arquitectura

El proyecto sigue una arquitectura en capas con separación clara de responsabilidades:

```
Vistas (Views) → Servicios (Services) → Repositorios (Repositories) → Base de datos (MySQL)
```

- **Views**: definen los endpoints REST y de página.
- **Services**: contienen la lógica de negocio.
- **Repositories**: encapsulan todas las consultas SQL.
- **Utils**: herramientas transversales (auth, seguridad, validación, correo).
- **Permissions**: permisos centralizados en `core/permissions.py`.

---

## Estructura de carpetas

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
├── .env
├── .gitignore
│
├── docker/
│   ├── Dockerfile               # Multi-stage: dev / prod
│   ├── docker-compose.yml       # Desarrollo: app + MySQL
│   ├── docker-compose.prod.yml  # Producción override
│   └── entrypoint.sh            # Espera MySQL, migra, arranca server
│
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── urls.py
│   ├── wsgi.py
│   └── settings/
│       ├── base.py              # Configuración común
│       ├── dev.py               # Desarrollo (DEBUG=True)
│       ├── prod.py              # Producción (DEBUG=False, seguridad)
│       └── test.py              # Testing (SQLite en memoria)
│
├── apps/
│   ├── __init__.py
│   ├── admin_panel/             # Panel de administración
│   ├── authentication/          # Registro, login, recuperación
│   ├── billing/                 # Facturación y pasarela de pago
│   ├── chatbot/                 # Chatbot IA con Gemini
│   ├── core/                    # Permisos, middlewares, utilidades
│   ├── documents/               # Documentos clínicos
│   ├── patients/                # Portal de pacientes
│   ├── professionals/           # Portal de profesionales
│   └── scheduling/              # Agendamiento de citas
│
├── static/
│   ├── css/
│   ├── js/
│   ├── img/
│   └── responsive/
│
├── templates/
│   ├── admin/
│   ├── auth/
│   ├── base/
│   ├── legal/
│   ├── patient/
│   └── professional/
│
└── tests/
    └── test_integration.py      # Integration tests (Django test client)
```

---

## Roles de usuario

| Rol | Descripción |
|---|---|
| **Paciente** | Agenda citas, consulta su evolución, usa el chatbot de IA y chatea con su terapeuta |
| **Profesional** | Gestiona su agenda, revisa pacientes asignados y genera reportes |
| **Administrador** | Panel completo: usuarios, roles, logs, métricas del servidor y configuración del chatbot |

---

## Instalación

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
- Crear un superuser de prueba (`admin@psyai.com` / `Admin123`)
- Arrancar el servidor de desarrollo

#### Comandos útiles con Docker

```bash
docker compose -f docker/docker-compose.yml up -d              # Arrancar en background
docker compose -f docker/docker-compose.yml logs -f app        # Ver logs de la app
docker compose -f docker/docker-compose.yml exec app bash      # Shell dentro del contenedor
docker compose -f docker/docker-compose.yml down               # Detener contenedores
docker compose -f docker/docker-compose.yml down -v            # Detener y eliminar volúmenes
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

---

## Testing

### Instalar dependencias de test

```bash
pip install -r requirements.txt
```

Las dependencias de testing incluidas son: `pytest`, `pytest-django`, `pytest-cov`.

### Ejecutar la suite completa

```bash
# Configurar settings de test (SQLite en memoria)
export DJANGO_SETTINGS_MODULE=config.settings.test

# Ejecutar todos los unit tests
pytest --tb=short -q

# Ejecutar solo un tipo de test
pytest apps/authentication/tests/ -v
pytest apps/billing/tests/ -v
```

### Ejecutar tests de una sola app

```bash
pytest apps/scheduling/tests/ -v
pytest apps/professionals/tests/ -v
pytest apps/chatbot/tests/ -v
pytest apps/documents/tests/ -v
pytest apps/patients/tests/ -v
pytest apps/admin_panel/tests/ -v
pytest apps/core/tests/ -v
```

### Ver reporte de cobertura

```bash
pytest --cov=apps --cov-report=term-missing
pytest --cov=apps --cov-report=html:htmlcov
# Abrir htmlcov/index.html en el navegador
```

### Tests dentro de Docker

```bash
docker compose -f docker/docker-compose.yml exec app python -m pytest apps/ -q
```

### Estructura de tests

Cada app tiene su carpeta `tests/` con:

- `conftest.py` — fixtures (mocks de repositorios, instancias de servicios)
- `test_services.py` — tests unitarios de la capa de servicios
- `test_views.py` — tests de endpoints HTTP (RequestFactory + mock de auth)
- `test_repositories.py` — tests de repositorios con `@pytest.mark.django_db`

Los tests unitarios corren sobre **SQLite en memoria** (configurado en `config/settings/test.py`), por lo que son rápidos y no dependen de MySQL. Los repositorios usan `@pytest.mark.django_db` para tests de base de datos reales contra SQLite.

Los **integration tests** (`tests/test_integration.py`) están marcados con `@pytest.mark.integration` y requieren MySQL corriendo. Se excluyen automáticamente en CI.

---

## Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `SECRET_KEY` | Clave secreta para firmar sesiones Django | `dev-insecure-key-change-me` |
| `PORT` | Puerto del servidor | `8000` |
| `DB_HOST` | Host de MySQL | `localhost` |
| `DB_PORT` | Puerto de MySQL | `3306` |
| `DB_USER` | Usuario de MySQL | `root` |
| `DB_PASSWORD` | Contraseña de MySQL | `root` |
| `DB_NAME` | Nombre de la base de datos | `psyai_connect` |
| `DB_ROOT_PASSWORD` | Password root de MySQL (solo Docker) | `rootpass` |
| `GEMINI_MODEL` | Modelo de Gemini | `gemini-3.5-flash-lite` |
| `GEMINI_THINKING_LEVEL` | Nivel de pensamiento | `low` |
| `GEMINI_API_KEY` | API key de Google Gemini | Para chatbot |
| `GEMINI_API_KEYS` | API keys separadas por coma (rotación) | Para chatbot |
| `EMAIL_HOST` | Servidor SMTP | `smtp.gmail.com` |
| `EMAIL_PORT` | Puerto SMTP | `587` |
| `EMAIL_USE_TLS` | Usar TLS | `True` |
| `EMAIL_HOST_USER` | Usuario SMTP | — |
| `EMAIL_HOST_PASSWORD` | Contraseña SMTP | — |
| `DEFAULT_FROM_EMAIL` | Dirección de envío | — |
| `LOGIN_RATE_LIMIT` | Límite para login | `60 per minute` |
| `REGISTER_RATE_LIMIT` | Límite para registro | `20 per minute` |
| `PASSWORD_RECOVERY_RATE_LIMIT` | Límite para recuperación | `10 per minute` |

---

## Variables de entorno para Docker

Las siguientes variables ya tienen defaults en `docker-compose.yml` y coinciden con `.env.example`:

```bash
DB_NAME=psyai_connect
DB_USER=psyai
DB_PASSWORD=psyai_pass
DB_HOST=db              # nombre del servicio MySQL en Docker
DB_PORT=3306
DB_ROOT_PASSWORD=rootpass
```

---

## Seguridad

- **CSRF**: protección habilitada por defecto en todos los formularios.
- **Rate limiting**: endpoints de autenticación protegidos contra abuso.
- **HSTS**: habilitado en producción (1 año, incluye subdominios).
- **SSL redirect**: forzado en producción.
- **Cookies seguras**: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `CSRF_COOKIE_HTTPONLY` en producción.
- **SECRET_KEY validation**: en producción, el servidor se niega a arrancar si `SECRET_KEY` no está configurada o usa el valor inseguro por defecto.
- **Content-Type nosniff**: `X-Content-Type-Options: nosniff` habilitado.
- **X-Frame-Options**: `DENY` para prevenir clickjacking.

---

## Características principales

- **Autenticación completa**: registro, login, recuperación de contraseña por correo y reset con token seguro.
- **Chatbot de triaje con IA**: integrado con Google Gemini, con prompt del sistema configurable desde el panel admin, caché de configuración, detección de palabras de riesgo y rotación automática de API keys.
- **Chat en tiempo real**: mensajería directa entre paciente y profesional usando Server-Sent Events (SSE).
- **Gestión de citas**: creación, visualización y seguimiento de citas por parte de pacientes y profesionales.
- **Historia clínica**: diagnósticos y documentos clínicos adjuntos, visibles para el paciente y gestionados por el profesional.
- **Evolución del paciente**: seguimiento del progreso terapéutico con entradas diarias.
- **Facturación**: creación de facturas, integración con pasarela de pago Wompi, gestión de estados y anulaciones.
- **Telemetría en vivo**: el panel admin muestra en tiempo real el uso de CPU, RAM, disco, número de peticiones, endpoints más usados y eventos de seguridad.
- **Sistema de temas**: soporte para modo claro y oscuro persistido por usuario.
- **Diseño responsivo**: CSS adaptativo para móvil, tablet y escritorio por cada sección.
- **Docker**: containerización lista para desarrollo y producción con hot-reload, MySQL persistente y migraciones automáticas. Archivos Docker organizados en `docker/`.
- **259+ tests**: unit tests e integration tests cubriendo las capas de servicios, repositorios y endpoints HTTP.

---

## Licencia

Este proyecto es de uso educativo/interno. Revisa el repositorio para más detalles sobre su licencia.
