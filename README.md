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

---

## Estructura de carpetas y archivos

```
PsyAI-Connect/
│
├── manage.py
├── requirements.txt
├── .env.example
├── .env
├── .gitignore
├── psyai_connect (4).sql
│
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── urls.py
│   ├── wsgi.py
│   └── settings/
│
├── apps/
│   ├── __init__.py
│   ├── admin_panel/
│   ├── authentication/
│   ├── billing/
│   ├── chatbot/
│   ├── core/
│   ├── documents/
│   ├── patients/
│   ├── professionals/
│   └── scheduling/
│
├── static/
│   ├── css/
│   ├── js/
│   ├── img/
│   └── responsive/
│
└── templates/
    ├── admin/
    ├── auth/
    ├── base/
    ├── legal/
    ├── patient/
    └── professional/
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
- MySQL 8+
- Una API key de [Google AI Studio](https://aistudio.google.com/) para el chatbot

### Instalación manual

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/PsyAI-Connect.git
cd PsyAI-Connect

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 5. Importar la base de datos
mysql -u root -p < "psyai_connect (4).sql"

# 6. Iniciar el servidor
python manage.py runserver
```

El servidor estará disponible en `http://127.0.0.1:8000`.

---

## Variables de entorno

| Variable | Descripción | Requerido |
|---|---|---|
| `SECRET_KEY` | Clave secreta para firmar sesiones Django | Sí (producción) |
| `PORT` | Puerto del servidor (por defecto: `8000`) | No |
| `DB_HOST` | Host de MySQL (por defecto: `localhost`) | No |
| `DB_PORT` | Puerto de MySQL (por defecto: `3306`) | No |
| `DB_USER` | Usuario de MySQL | No |
| `DB_PASSWORD` | Contraseña de MySQL | No |
| `DB_NAME` | Nombre de la base de datos | No |
| `GEMINI_API_KEY` | API key de Google Gemini (una sola) | Para chatbot |
| `GEMINI_API_KEYS` | API keys separadas por coma (rotación automática) | Para chatbot |
| `BREVO_API_KEY` | API key de Brevo para correos transaccionales | Para correos |
| `BREVO_FROM` | Dirección de envío verificada en Brevo | Para correos |
| `BREVO_FROM_NAME` | Nombre del remitente | Para correos |
| `LOGIN_RATE_LIMIT` | Límite para login | No |
| `REGISTER_RATE_LIMIT` | Límite para registro | No |
| `PASSWORD_RECOVERY_RATE_LIMIT` | Límite para recuperar/restablecer contraseña | No |
| `LOG_LEVEL` | Nivel de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | No |

---

## Características principales

- **Autenticación completa**: registro, login, recuperación de contraseña por correo y reset con token seguro.
- **Chatbot de triaje con IA**: integrado con Google Gemini, con prompt del sistema configurable desde el panel admin, caché de configuración, detección de palabras de riesgo y rotación automática de API keys.
- **Chat en tiempo real**: mensajería directa entre paciente y profesional usando Server-Sent Events (SSE).
- **Gestión de citas**: creación, visualización y seguimiento de citas por parte de pacientes y profesionales.
- **Historia clínica**: diagnósticos y documentos clínicos adjuntos, visibles para el paciente y gestionados por el profesional.
- **Evolución del paciente**: seguimiento del progreso terapéutico con entradas diarias.
- **Telemetría en vivo**: el panel admin muestra en tiempo real el uso de CPU, RAM, disco, número de peticiones, endpoints más usados y eventos de seguridad.
- **Sistema de temas**: soporte para modo claro y oscuro persistido por usuario.
- **Diseño responsivo**: CSS adaptativo para móvil, tablet y escritorio por cada sección.
- **Rate limiting**: protección de endpoints sensibles contra abuso, con configuración diferenciada por entorno.
- **CSRF**: protección contra Cross-Site Request Forgery habilitada por defecto en todos los formularios.

---

## Licencia

Este proyecto es de uso educativo/interno. Revisa el repositorio para más detalles sobre su licencia.