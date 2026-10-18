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

## 📚 Documentación Técnica

Toda la docs detallada en [`docs/`](docs/):

| Archivo | Contenido |
|---------|-----------|
| [`docs/api.md`](docs/api.md) | Referencia endpoints REST |
| [`docs/seguridad.md`](docs/seguridad.md) | Hardening y estado seguridad |
| [`docs/modelos-de-datos.md`](docs/modelos-de-datos.md) | Modelo ER y diccionario datos |
| [`docs/roles-y-permisos.md`](docs/roles-y-permisos.md) | Roles, pantallas, permisos DRF |
| [`docs/frontend.md`](docs/frontend.md) | Arquitectura JS/CSS/Tema/Alertas |
| [`docs/chatbot-ia.md`](docs/chatbot-ia.md) | Integración Gemini profunda |
| [`docs/pagos-facturacion.md`](docs/pagos-facturacion.md) | Flujo facturación + Wompi |
| [`docs/despliegue.md`](docs/despliegue.md) | Docker, variables, producción |
| [`docs/testing.md`](docs/testing.md) | Estrategia tests, capas, CI |

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