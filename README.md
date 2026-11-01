<div align="center">

# 🧠 PsyAI Connect

**Plataforma integral de gestión para consultorios de psicología con IA integrada**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white)](https://djangoproject.com)
[![DRF](https://img.shields.io/badge/DRF-3.14-ff1709?logo=django&logoColor=white)](https://django-rest-framework.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://mysql.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-259%2B-brightgreen)](#-testing)
[![License](https://img.shields.io/badge/License-Educational-blue)](#-licencia)

*Conecta pacientes con profesionales, automatiza el triaje con IA y centraliza la operación clínica en una sola plataforma.*

</div>

---

## 🎯 Objetivo

Digitalizar y centralizar la operación de consultorios y redes de psicólogos mediante tres portales especializados:

| Portal | Funcionalidades clave |
|--------|----------------------|
| 👤 **Pacientes** | Agendar citas · Ver evolución · Chat con terapeuta · Chatbot de apoyo IA |
| 👩‍⚕️ **Profesionales** | Gestión de agenda · Historial de pacientes · Generación de reportes |
| ⚙️ **Administración** | Métricas en tiempo real · Usuarios y roles · Logs · Configuración del chatbot IA |

---

## 🛠 Stack Tecnológico

### Backend
| Tech | Propósito |
|------|-----------|
| **Python 3.10+** | Lenguaje principal |
| **Django 5** | Framework web robusto |
| **Django REST Framework** | APIs REST versionadas |
| **MySQL 8** | Base de datos relacional |
| **Waitress** | Servidor WSGI producción |
| **python-dotenv** | Configuración por entorno |
| **psutil** | Métricas sistema (CPU/RAM/Disco) |
| **bcrypt** | Hash seguro de contraseñas |
| **Brevo** | Correos transaccionales |

### Inteligencia Artificial
| Tech | Uso |
|------|-----|
| **Google Gemini API** | Chatbot de triaje psicológico |
| **Rotación multi-key** | Distribución de cuota entre proyectos |

### Frontend
| Tech | Uso |
|------|-----|
| **Bootstrap 5 + Django Templates** | Renderizado servidor |
| **CSS modular** | Temas, responsividad, componentes |
| **Vanilla JS (ES6+)** | Lógica UI por módulo |
| **SSE** | Tiempo real en chat y panel admin |

### Testing & DevOps
`pytest` · `pytest-django` · `pytest-cov` · `Docker` · `Docker Compose`

---

## 🏗 Arquitectura

```
Views → Services → Repositories → MySQL
```

- **Views** — Endpoints REST y páginas
- **Services** — Lógica de negocio pura
- **Repositories** — Consultas SQL encapsuladas
- **Utils** — Auth, seguridad, validación, correo
- **Permissions** — Centralizadas en `core/permissions.py`

---

## 📁 Estructura del Proyecto

<details>
<summary>Ver árbol completo</summary>

```
PsyAI-Connect/
├── manage.py
├── requirements.txt
├── setup_install.py          # Instalador automático
├── pytest.ini
├── conftest.py
├── .env.example
├── .gitignore
│
├── install/
│   ├── Dockerfile            # Multi-stage dev/prod
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── entrypoint.sh
│
├── config/
│   └── settings/             # base, dev, prod, test
│
├── apps/
│   ├── admin_panel/          # Panel administración
│   ├── authentication/       # Auth completa
│   ├── billing/              # Facturación + Wompi
│   ├── chatbot/              # IA Gemini
│   ├── core/                 # Permisos, middlewares
│   ├── documents/            # Documentos clínicos
│   ├── patients/             # Portal pacientes
│   ├── professionals/        # Portal profesionales
│   └── scheduling/           # Agendamiento citas
│
├── static/                   # CSS, JS, imágenes
└── templates/                # Plantillas Django
```
</details>

---

## 👥 Roles de Usuario

| Rol | Permisos |
|-----|----------|
| **Paciente** | Citas, evolución, chatbot IA, chat terapeuta |
| **Profesional** | Agenda, pacientes asignados, reportes |
| **Administrador** | Panel completo: usuarios, roles, logs, métricas, config IA |

---

## 🚀 Instalación Rápida

### Prerrequisitos
- Python 3.10+
- MySQL 8+ (o Docker)
- API Key de [Google AI Studio](https://aistudio.google.com/)

### 🐳 Con Docker (Recomendado)

```bash
# 1. Clonar
git clone https://github.com/ArleyRojo/PsyAI-Connect.git
cd PsyAI-Connect

# 2. Configurar entorno
cp .env.example .env
# Editar .env con SECRET_KEY y credenciales

# 3. Levantar
docker compose -f install/docker-compose.yml up
```
🎉 **Listo** en `http://localhost:8000`  
El entrypoint crea BD, migra, crea superuser demo (`admin@psyai.com` / `Admin123`) y arranca el servidor.

### 💻 Instalación Manual

```bash
git clone https://github.com/ArleyRojo/PsyAI-Connect.git
cd PsyAI-Connect

python -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\activate       # Windows

pip install -r requirements.txt
cp .env.example .env
# Configurar .env

mysql -u root -p -e "CREATE DATABASE psyai_connect CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

python manage.py migrate
python manage.py createsuperuser  # opcional
python manage.py runserver
```

---

## 🧪 Testing

```bash
# Configurar settings de test
export DJANGO_SETTINGS_MODULE=config.settings.test

# Suite completa
pytest --tb=short -q

# Con cobertura
pytest --cov=apps --cov-report=term-missing
pytest --cov=apps --cov-report=html:htmlcov  # Abrir htmlcov/index.html

# Por app
pytest apps/chatbot/tests/ -v
pytest apps/scheduling/tests/ -v

# En Docker
docker compose -f install/docker-compose.yml exec app python -m pytest apps/ -q
```

> **259+ tests** cubriendo servicios, repositorios, vistas y endpoints HTTP.  
> Unit tests usan **SQLite en memoria** (rápidos, sin MySQL).  
> Integration tests marcados con `@pytest.mark.integration` requieren MySQL.

---

## ⚙️ Variables de Entorno Clave

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `SECRET_KEY` | Clave secreta Django | ✅ |
| `GEMINI_API_KEY` / `GEMINI_API_KEYS` | API keys Gemini (rotación multi-key) | ✅ |
| `DB_*` | Conexión MySQL (host, port, user, pass, name) | ✅ |
| `EMAIL_*` | SMTP para correos transaccionales | ✅ |
| `LOGIN_RATE_LIMIT` | Rate limit login (default: `60/m`) | ❌ |

Ver `.env.example` para lista completa.

---

## 🔒 Seguridad

- ✅ CSRF en todos los formularios
- ✅ Rate limiting en auth endpoints
- ✅ HSTS + SSL Redirect en producción
- ✅ Cookies seguras (Secure, HttpOnly, SameSite)
- ✅ Validación estricta de `SECRET_KEY` en prod
- ✅ `X-Content-Type-Options: nosniff`
- ✅ `X-Frame-Options: DENY`

---

## ✨ Características Destacadas

| Feature | Detalle |
|---------|---------|
| 🔐 **Auth completa** | Registro, login, recovery, reset con tokens seguros |
| 🤖 **Chatbot IA** | Gemini con prompt configurable, caché, detección de riesgo, rotación multi-key |
| 💬 **Chat tiempo real** | SSE bidireccional paciente–profesional |
| 📅 **Agendamiento** | Citas con estados, recordatorios, conflictos |
| 📋 **Historia clínica** | Diagnósticos + documentos adjuntos |
| 📈 **Evolución paciente** | Seguimiento diario del progreso |
| 💳 **Facturación** | Facturas + integración Wompi |
| 📊 **Telemetría live** | CPU, RAM, disco, peticiones, endpoints, eventos seguridad |
| 🌓 **Temas** | Claro/oscuro persistido por usuario |
| 📱 **Responsive** | Móvil, tablet, desktop por sección |
| 🐳 **Docker ready** | Dev (hot-reload) + Prod (Waitress) |
| ✅ **Tests** | 259+ unit + integration |

---

## 📄 Documentación

Abre los documentos del proyecto desde el último release de GitHub:

| Documento | Ver |
|-----------|-----|
| Casos de uso | [Ver PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FCasos_de_Uso_PsyAI_Connect_1.pdf&embedded=true) |
| Historias de usuario | [Ver PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FHistorias_de_Usuario_PsyAI_Connect.pdf&embedded=true) |
| Manual de usuario | [Ver PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FManual_Usuario_PsyAI_Connect_1.1.pdf&embedded=true) |
| Matriz de requisitos | [Ver XLSX](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FMatriz_de_requisitos_PsyAi_Connect_actualizada_v2.xlsx&embedded=true) |
| Mockups | [Ver PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2Fmockups.1.pdf&embedded=true) |
| Diagramas UML | [Ver PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FPsyAI_Connect_Diagramas_UML.pdf&embedded=true) |
| Guía de marca | [Ver PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FPsyAI-Connect-Guia-de-marca.pdf&embedded=true) |
| Mapa de navegación | [Ver PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FPsyAI-Connect-Mapa-de-navegacion-oscuro.1.pdf&embedded=true) |

---

## 📚 Documentación Técnica

Consulta la documentación técnica completa organizada por área. Este `README.md` es la puerta de entrada del proyecto; el resto de los documentos detallados se encuentran en la carpeta [`docs/`](docs/).

| Documento | Descripción | Acceso |
|-----------|-------------|--------|
| 📘 **README.md** | Índice de la carpeta `docs/`: resume toda la documentación técnica detallada (API, seguridad, modelos, roles, frontend, chatbot IA, despliegue, testing, integraciones). El README de la raíz sigue siendo la puerta de entrada general. | [Ver documento](docs/README.md) |
| 🏗 **architecture.md** | Arquitectura general del sistema: capas Views → Services → Repositories, módulos por app y diagrama de componentes. | [docs/architecture.md](docs/architecture.md) |
| 🔌 **api.md** | Referencia de API REST: endpoints por app, métodos HTTP, autenticación requerida y roles permitidos. | [docs/api.md](docs/api.md) |
| 🔒 **security.md** | Seguridad y protección de datos: capas de hardening, CSRF, rate limiting, cookies seguras, HSTS y buenas prácticas. | [docs/security.md](docs/security.md) |
| 🚀 **deployment.md** | Instalación y despliegue: Docker multi-stage, compose dev/prod, entrypoint y variables de entorno. | [docs/deployment.md](docs/deployment.md) |
| 🧪 **testing.md** | Estrategia de pruebas: organización con pytest, cobertura, capas repository/service/view y tests de integración. | [docs/testing.md](docs/testing.md) |
| 👥 **roles-and-permissions.md** | Roles y permisos: tres roles de usuario, pantallas por rol y clases de permiso de Django REST Framework. | [docs/roles-and-permissions.md](docs/roles-and-permissions.md) |
| 🗄 **data-models.md** | Modelos y relaciones de datos: modelos por app, campos clave, claves foráneas y diagrama ER en Mermaid. | [docs/data-models.md](docs/data-models.md) |
| 🎨 **frontend.md** | Arquitectura del frontend: organización de JS y CSS, temas claro/oscuro, sistema de alertas y convenciones. | [docs/frontend.md](docs/frontend.md) |
| 🤖 **chatbot-ai.md** | Chatbot e integración con Gemini: flujo de mensajería, rotación de API keys y detección de riesgo emocional. | [docs/chatbot-ai.md](docs/chatbot-ai.md) |
| 🔗 **integrations.md** | Integraciones externas: Gemini IA, Twilio WhatsApp, Google OAuth (allauth), correo SMTP, pagos manuales con evidencia y boletín informativo. | [docs/integrations.md](docs/integrations.md) |

---

## 🤝 Contribuir

1. Fork del repo
2. Crea tu feature branch: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Abre un Pull Request

---

## 📄 Licencia

Uso educativo/interno. Consulta el repositorio para detalles de licencia.

---

## 👨‍💻 Autor

**Arley Rojo** — [GitHub](https://github.com/ArleyRojo)

---

<div align="center">

⭐ **¿Te gusta el proyecto? Dale una estrella en GitHub**

</div>

---

## English Version

# 🧠 PsyAI Connect

**Integrated psychology clinic management platform with AI**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white)](https://djangoproject.com)
[![DRF](https://img.shields.io/badge/DRF-3.14-ff1709?logo=django&logoColor=white)](https://django-rest-framework.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://mysql.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-259%2B-brightgreen)](#-testing)
[![License](https://img.shields.io/badge/License-Educational-blue)](#-license)

*Connects patients with professionals, automates triage with AI and centralizes clinical operation in a single platform.*

---

## 🎯 Objective / Objetivo

Digitize and centralize the operation of psychology offices and psychologist networks through three specialized portals:

| Portal | Key functionalities |
|--------|--------------------|
| 👤 **Patients** | Schedule appointments · View evolution · Therapist chat · AI support chatbot |
| 👩‍⚕️ **Professionals** | Schedule management · Patient history · Report generation |
| ⚙️ **Administration** | Real-time metrics · Users and roles · Logs · AI chatbot configuration |

---

## 📄 Documentation / Documentación

Open project documents from the latest GitHub release:

| Document | View |
|----------|------|
| Use cases | [View PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FCasos_de_Uso_PsyAI_Connect_1.pdf&embedded=true) |
| User stories | [View PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FHistorias_de_Usuario_PsyAI_Connect.pdf&embedded=true) |
| User manual | [View PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FManual_Usuario_PsyAI_Connect_1.1.pdf&embedded=true) |
| Requirements matrix | [View XLSX](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FMatriz_de_requisitos_PsyAi_Connect_actualizada_v2.xlsx&embedded=true) |
| Mockups | [View PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2Fmockups.1.pdf&embedded=true) |
| UML diagrams | [View PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FPsyAI_Connect_Diagramas_UML.pdf&embedded=true) |
| Brand guide | [View PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FPsyAI-Connect-Guia-de-marca.pdf&embedded=true) |
| Navigation map | [View PDF](https://docs.google.com/viewer?url=https%3A%2F%2Fgithub.com%2FManuelRojas22%2FPsyAi-Connect%2Freleases%2Flatest%2Fdownload%2FPsyAI-Connect-Mapa-de-navegacion-oscuro.1.pdf&embedded=true) |

---

## 🛠 Technological stack / Stack Tecnológico

### Backend

| Tech | Purpose |
|------|---------|
| **Python 3.10+** | Main language |
| **Django 5** | Robust web framework |
| **Django REST Framework** | Versioned REST APIs |
| **MySQL 8** | Relational database |
| **Waitress** | Production WSGI server |
| **python-dotenv** | Environment-based configuration |
| **psutil** | System metrics (CPU/RAM/Disk) |
| **bcrypt** | Secure password hashing |
| **Brevo** | Transactional emails |

### Artificial Intelligence

| Tech | Use |
|------|-----|
| **Google Gemini API** | Psychological triage chatbot |
| **Multi-key rotation** | Quota distribution across projects |

### Frontend

| Tech | Use |
|------|-----|
| **Bootstrap 5 + Django Templates** | Server-side rendering |
| **CSS modular** | Themes, responsiveness, components |
| **Vanilla JS (ES6+)** | UI logic per module |
| **SSE** | Real-time chat and admin panel |

### Testing & DevOps

`pytest` · `pytest-django` · `pytest-cov` · `Docker` · `Docker Compose`

---

## 🏗 Architecture / Arquitectura

```
Views → Services → Repositories → MySQL
```

- **Views** — REST endpoints and pages
- **Services** — Pure business logic
- **Repositories** — Encapsulated SQL queries
- **Utils** — Auth, security, validation, email
- **Permissions** — Centralized in `core/permissions.py`

---

## 📁 Project structure / Estructura del Proyecto

<details>
<summary>View full tree / Ver árbol completo</summary>

```
PsyAI-Connect/
├── manage.py
├── requirements.txt
├── setup_install.py          # Automatic installer
├── pytest.ini
├── conftest.py
├── .env.example
├── .gitignore
│
├── install/
│   ├── Dockerfile            # Multi-stage dev/prod
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── entrypoint.sh
│
├── config/
│   └── settings/             # base, dev, prod, test
│
├── apps/
│   ├── admin_panel/          # Administration panel
│   ├── authentication/       # Complete auth
│   ├── billing/              # Billing + Wompi
│   ├── chatbot/              # Gemini AI
│   ├── core/                 # Permissions, middlewares
│   ├── documents/            # Clinical documents
│   ├── patients/             # Patient portal
│   ├── professionals/        # Professional portal
│   └── scheduling/           # Appointment scheduling
│
├── static/                   # CSS, JS, images
└── templates/                # Django templates
```
</details>

---

## 👥 User roles / Roles de Usuario

| Role | Permissions |
|------|-------------|
| **Patient** | Appointments, evolution, AI chatbot, therapist chat |
| **Professional** | Agenda, assigned patients, reports |
| **Administrator** | Full panel: users, roles, logs, metrics, AI config |

---

## 🚀 Quick installation / Instalación Rápida

### Prerequisites / Prerrequisitos
- Python 3.10+
- MySQL 8+ (or Docker)
- API Key from [Google AI Studio](https://aistudio.google.com/)

### 🐳 With Docker (Recommended)

```bash
# 1. Clone
git clone https://github.com/ArleyRojo/PsyAI-Connect.git
cd PsyAI-Connect

# 2. Configure environment
cp .env.example .env
# Edit .env with SECRET_KEY and credentials

# 3. Start
docker compose -f install/docker-compose.yml up
```

🎉 **Ready** at `http://localhost:8000`  
The entrypoint creates DB, migrates, creates demo superuser (`admin@psyai.com` / `Admin123`) and starts the server.

### 💻 Manual installation / Instalación Manual

```bash
git clone https://github.com/ArleyRojo/PsyAI-Connect.git
cd PsyAI-Connect

python -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\activate       # Windows

pip install -r requirements.txt
cp .env.example .env
# Configure .env

mysql -u root -p -e "CREATE DATABASE psyai_connect CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

python manage.py migrate
python manage.py createsuperuser  # optional
python manage.py runserver
```

---

## 🧪 Testing

```bash
# Configure test settings
export DJANGO_SETTINGS_MODULE=config.settings.test

# Full suite
pytest --tb=short -q

# With coverage
pytest --cov=apps --cov-report=term-missing
pytest --cov=apps --cov-report=html:htmlcov  # Open htmlcov/index.html

# By app
pytest apps/chatbot/tests/ -v
pytest apps/scheduling/tests/ -v

# In Docker
docker compose -f install/docker-compose.yml exec app python -m pytest apps/ -q
```

> **259+ tests** covering services, repositories, views and HTTP endpoints.  
> Unit tests use **SQLite in memory** (fast, no MySQL).  
> Integration tests marked with `@pytest.mark.integration` require MySQL.

---

## ⚙️ Key environment variables / Variables de Entorno Clave

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | ✅ |
| `GEMINI_API_KEY` / `GEMINI_API_KEYS` | Gemini API keys (multi-key rotation) | ✅ |
| `DB_*` | MySQL connection (host, port, user, pass, name) | ✅ |
| `EMAIL_*` | SMTP for transactional emails | ✅ |
| `LOGIN_RATE_LIMIT` | Login rate limit (default: `60/m`) | ❌ |

See `.env.example` for complete list.

---

## 🔒 Security

- ✅ CSRF on all forms
- ✅ Rate limiting on auth endpoints
- ✅ HSTS + SSL Redirect in production
- ✅ Secure cookies (Secure, HttpOnly, SameSite)
- ✅ Strict `SECRET_KEY` validation in prod
- ✅ `X-Content-Type-Options: nosniff`
- ✅ `X-Frame-Options: DENY`

---

## ✨ Featured features / Características Destacadas

| Feature | Detail |
|---------|--------|
| 🔐 **Complete auth** | Registration, login, recovery, reset with secure tokens |
| 🤖 **AI chatbot** | Gemini with configurable prompt, cache, risk detection, multi-key rotation |
| 💬 **Real-time chat** | Bidirectional SSE patient–professional |
| 📅 **Scheduling** | Appointments with states, reminders, conflicts |
| 📋 **Clinical history** | Diagnoses + attached documents |
| 📈 **Patient evolution** | Daily progress tracking |
| 💳 **Billing** | Invoices + Wompi integration |
| 📊 **Live telemetry** | CPU, RAM, disk, requests, endpoints, security events |
| 🌓 **Themes** | Light/dark persisted per user |
| 📱 **Responsive** | Mobile, tablet, desktop per section |
| 🐳 **Docker ready** | Dev (hot-reload) + Prod (Waitress) |
| ✅ **Tests** | 259+ unit + integration |

---

## 📚 Technical documentation / Documentación Técnica

Consult the complete technical documentation organized by area. This `README.md` is the project's entry point; the rest of the detailed documents are in the [`docs/`](docs/) folder.

| Document | Description | Access |
|----------|-------------|--------|
| 📘 **README.md** | Documentation index of the `docs/` folder: summarizes all detailed technical documentation (API, security, models, roles, frontend, chatbot AI, deployment, testing, integrations). The root `README.md` remains the general entry point. | [docs/README.md](docs/README.md) |
| 🏗 **architecture.md** | General system architecture: Views → Services → Repositories layers, per-app modules and component diagram. | [docs/architecture.md](docs/architecture.md) |
| 🔌 **api.md** | REST API reference: endpoints by app, HTTP methods, required authentication and allowed roles. | [docs/api.md](docs/api.md) |
| 🔒 **security.md** | Security and data protection: hardening layers, CSRF, rate limiting, secure cookies, HSTS and best practices. | [docs/security.md](docs/security.md) |
| 🚀 **deployment.md** | Installation and deployment: multi-stage Docker, compose dev/prod, entrypoint and environment variables. | [docs/deployment.md](docs/deployment.md) |
| 🧪 **testing.md** | Testing strategy: pytest organization, coverage, repository/service/view layers and integration tests. | [docs/testing.md](docs/testing.md) |
| 👥 **roles-and-permissions.md** | Roles and permissions: three user roles, screens per role and Django REST Framework permission classes. | [docs/roles-and-permissions.md](docs/roles-and-permissions.md) |
| 🗄 **data-models.md** | Data models and relationships: per-app models, key fields, foreign keys and Mermaid ER diagram. | [docs/data-models.md](docs/data-models.md) |
| 🎨 **frontend.md** | Frontend architecture: JS and CSS organization, light/dark theme, alert system and conventions. | [docs/frontend.md](docs/frontend.md) |
| 🤖 **chatbot-ai.md** | Chatbot and Gemini integration: messaging flow, API key rotation and emotional risk detection. | [docs/chatbot-ai.md](docs/chatbot-ai.md) |
| 🔗 **integrations.md** | External integrations: Gemini AI, Twilio WhatsApp, Google OAuth (allauth), SMTP email, manual payments with evidence and newsletter. | [docs/integrations.md](docs/integrations.md) |

---

## 🤝 Contributing

1. Fork the repo
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

Educational/internal use. Consult the repository for license details.

---

## 👨‍💻 Author

**Arley Rojo** — [GitHub](https://github.com/ArleyRojo)

---

<div align="center">

⭐ **If you like the project, give it a star on GitHub**

</div>