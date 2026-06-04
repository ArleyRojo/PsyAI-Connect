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
| **Flask 3** | Framework web |
| **Flask-CORS** | Manejo de políticas de origen cruzado |
| **Flask-Limiter** | Rate limiting por IP para proteger las APIs |
| **MySQL** | Base de datos relacional |
| **mysql-connector-python** | Driver de conexión a MySQL |
| **Waitress** | Servidor WSGI para producción |
| **python-dotenv** | Gestión de variables de entorno |
| **psutil** | Métricas del sistema (CPU, RAM, disco) |
| **requests** | Cliente HTTP |
| **filetype** | Validación de tipo de archivos subidos |

### Inteligencia Artificial
| Tecnología | Uso |
|---|---|
| **Google Gemini API** | Chatbot de triaje psicológico para pacientes |

La integración con Gemini soporta **rotación automática de API keys** para distribuir cuota entre múltiples proyectos de Google AI Studio.

### Frontend
| Tecnología | Uso |
|---|---|
| **HTML / Jinja2 / Boostrap 5.0.2** | Plantillas del servidor |
| **CSS personalizado** | Estilos por módulo, tema y responsividad |
| **JavaScript vanilla** | Lógica de UI por módulo (sin frameworks) |
| **SSE (Server-Sent Events)** | Actualizaciones en tiempo real en el panel admin |

---

## Arquitectura

El proyecto sigue una arquitectura en capas con separación clara de responsabilidades:

```
Rutas (Routes) → Servicios (Services) → Repositorios (Repositories) → Base de datos (MySQL)
```

- **Routes**: definen los endpoints REST y de página.
- **Services**: contienen la lógica de negocio.
- **Repositories**: encapsulan todas las consultas SQL.
- **Utils**: herramientas transversales (auth, seguridad, validación, correo).

---

## Estructura de carpetas

```
PsyAI-Connect/
│
├── run.py                        # Punto de entrada, inicia el servidor Flask
├── setup_install.py              # Script de instalación/configuración inicial
├── requirements.txt              # Dependencias Python del proyecto
├── .env.example                  # Plantilla de variables de entorno
├── psyai_connect.sql             # Dump de la base de datos MySQL
│
└── app/
    │
    ├── __init__.py               # Factory de la app Flask (create_app)
    ├── config.py                 # Configuración de la app y logging
    │
    ├── database/
    │   ├── connection.py         # Pool de conexiones a MySQL
    │   └── migrations.py        # Inicialización/migración del esquema
    │
    ├── routes/                   # Endpoints REST y rutas de páginas
    │   ├── admin_routes.py
    │   ├── appointment_routes.py
    │   ├── auth_routes.py
    │   ├── page_routes.py
    │   ├── patient_routes.py
    │   ├── professional_routes.py
    │   └── theme_routes.py
    │
    ├── services/                 # Lógica de negocio
    │   ├── admin_service.py
    │   ├── appointment_service.py
    │   ├── auth_service.py
    │   ├── chat_events.py        # SSE para chat en tiempo real
    │   ├── chatbot_config_events.py
    │   ├── chatbot_config_service.py
    │   ├── chatbot_service.py    # Integración con Google Gemini
    │   ├── patient_service.py
    │   ├── professional_service.py
    │   └── telemetry_service.py  # Métricas en memoria (CPU, RAM, requests)
    │
    ├── repositories/             # Acceso a datos (SQL)
    │   ├── admin_repository.py
    │   ├── appointment_repository.py
    │   ├── auth_repository.py
    │   ├── chat_repository.py
    │   ├── chatbot_config_repository.py
    │   ├── mensajes_repository.py
    │   ├── patient_repository.py
    │   └── professional_repository.py
    │
    ├── utils/                    # Utilidades transversales
    │   ├── auth.py               # Decoradores de autenticación y sesión
    │   ├── db.py                 # Context manager para cursor de DB
    │   ├── exceptions.py         # Excepciones personalizadas
    │   ├── mail.py               # Envío de correos SMTP
    │   ├── security.py           # Hash de contraseñas, tokens
    │   └── validators.py         # Validación de datos de entrada
    │
    ├── templates/                # Plantillas HTML (Jinja2)
    │   ├── base/
    │   │   └── index.html        # Landing page
    │   ├── auth/
    │   │   ├── login.html
    │   │   ├── register.html
    │   │   ├── recover.html
    │   │   └── reset-password.html
    │   ├── patient/
    │   │   ├── patient.dashboard.html
    │   │   └── aside-patient/
    │   │       ├── agenda-quotes.html
    │   │       ├── chatbot.html
    │   │       ├── evolution.html
    │   │       ├── mensajes.html
    │   │       └── my.profile.html
    │   ├── professional/
    │   │   ├── professional.dashboard.html
    │   │   └── aside-professional/
    │   │       ├── my.agenda.html
    │   │       ├── patients.html
    │   │       ├── reports.html
    │   │       ├── mensajes.html
    │   │       └── my.profile2.html
    │   └── admin/
    │       ├── admin.dashboard.html
    │       └── aside-admin/
    │           ├── users.html
    │           ├── roles.html
    │           ├── logs.html
    │           ├── notifications.html
    │           └── chatbot.config.html
    │
    └── static/
        ├── css/
        │   ├── base/             # Estilos base y animaciones
        │   ├── components/       # Componentes reutilizables y alertas
        │   ├── layout/           # Estructura general de la página
        │   ├── pages/            # Estilos por rol (admin, patient, professional)
        │   └── themes/           # Sistema de temas (claro/oscuro)
        ├── js/
        │   ├── base/             # Scripts de la landing
        │   ├── core/shared/      # Utilidades compartidas (tema, alertas, navbar)
        │   └── modules/          # Lógica JS por módulo y rol
        │       ├── admin/
        │       ├── auth/
        │       ├── patient/
        │       ├── professional/
        │       └── shared/
        ├── responsive/           # CSS adaptativo por sección
        ├── img/                  # Imágenes del proyecto
        └── uploads/              # Archivos subidos por usuarios
```

---

## Roles de usuario

| Rol | Descripción |
|---|---|
| **Paciente** | Agenda citas, consulta su evolución, usa el chatbot de IA y chatea con su terapeuta |
| **Profesional** | Gestiona su agenda, revisa pacientes asignados y genera reportes |
| **Administrador** | Panel completo: usuarios, roles, logs, métricas del servidor y configuración del chatbot |

---

## APIs REST

### Autenticación (`/api/`)

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/register` | Registro de nuevo usuario |
| `POST` | `/api/login` | Inicio de sesión |
| `POST` | `/api/logout` | Cierre de sesión |
| `GET` | `/api/session` | Verificar sesión activa y obtener datos del usuario |
| `POST` | `/api/forgot-password` | Solicitar correo de recuperación de contraseña |
| `POST` | `/api/reset-password` | Restablecer contraseña con token |

---

### Paciente (`/api/`)

#### Perfil
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/perfil/paciente/<id_usuario>` | Obtener perfil de un paciente |
| `PUT` | `/api/perfil/paciente` | Actualizar perfil del paciente |
| `POST` | `/api/perfil/foto` | Subir foto de perfil |

#### Evolución y datos clínicos
| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/evolucion` | Registrar entrada de evolución |
| `GET` | `/api/evolucion` | Obtener historial de evolución del paciente |

#### Chatbot IA
| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/chatbot/enviar` | Enviar mensaje al chatbot Gemini |
| `GET` | `/api/chatbot/config` | Obtener configuración activa del chatbot |
| `GET` | `/api/chatbot/config/events` | SSE: actualizaciones en vivo de config del chatbot |
| `GET` | `/api/chatbot/historial` | Obtener historial de conversación con el chatbot |
| `DELETE` | `/api/chatbot/historial` | Eliminar historial del chatbot |
| `POST` | `/api/chatbot/encuesta` | Enviar encuesta de satisfacción del chatbot |
| `GET` | `/api/paciente/consentimiento-chatbot` | Verificar consentimiento del paciente para chatbot |
| `POST` | `/api/paciente/consentimiento-chatbot` | Registrar consentimiento del paciente |

#### Chat con profesional
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/chat/profesionales` | Listar profesionales disponibles para chatear |
| `GET` | `/api/chat/mensajes` | Obtener mensajes del chat con el profesional |
| `GET` | `/api/paciente/chat/mensajes` | Alias: mensajes del chat (ruta alternativa) |
| `POST` | `/api/chat/enviar` | Enviar mensaje al profesional |
| `POST` | `/api/paciente/chat/enviar` | Alias: enviar mensaje (ruta alternativa) |

#### Directorio
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/pacientes` | Listar pacientes (uso interno) |
| `GET` | `/api/profesionales` | Listar profesionales disponibles |

---

### Profesional (`/api/`)

#### Perfil y disponibilidad
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/perfil/profesional/<id_usuario>` | Obtener perfil de un profesional |
| `PUT` | `/api/perfil/profesional` | Actualizar perfil del profesional |
| `POST` | `/api/disponibilidad` | Configurar horarios de disponibilidad |
| `GET` | `/api/disponibilidad/<id_profesional>` | Obtener disponibilidad de un profesional |

#### Dashboard y pacientes
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/profesional/dashboard` | Obtener datos del dashboard del profesional |
| `GET` | `/api/profesional/pacientes` | Listar pacientes asignados al profesional |
| `GET` | `/api/evolucion/profesional` | Ver evolución de los pacientes del profesional |
| `GET` | `/api/profesional/paciente/<id_paciente>/chatbot-historial` | Ver historial de chatbot de un paciente |

#### Diagnósticos
| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/diagnosticos` | Crear diagnóstico para un paciente |
| `GET` | `/api/diagnosticos` | Obtener diagnósticos |

#### Reportes
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/reportes/profesional` | Listar reportes del profesional |
| `GET` | `/api/reportes/eliminados` | Listar reportes eliminados |
| `POST` | `/api/reportes` | Crear nuevo reporte |
| `PUT` | `/api/reportes/<id_reporte>` | Editar reporte |
| `DELETE` | `/api/reportes/<id_reporte>` | Eliminar reporte |

#### Chat con pacientes
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/chat/pacientes` | Listar pacientes disponibles para chatear |
| `GET` | `/api/profesional/chat/mensajes` | Obtener mensajes del chat con un paciente |
| `POST` | `/api/profesional/chat/enviar` | Enviar mensaje a un paciente |

---

### Citas (`/api/citas`)

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/citas` | Solicitar nueva cita |
| `GET` | `/api/citas/disponibles` | Obtener horarios disponibles |
| `GET` | `/api/citas/fechas-disponibles` | Obtener fechas con disponibilidad |
| `GET` | `/api/citas/proxima` | Obtener próxima cita del paciente |
| `GET` | `/api/citas/paciente` | Listar citas del paciente |
| `GET` | `/api/citas/profesional` | Listar citas del profesional |
| `GET` | `/api/citas/profesional/horarios` | Obtener horarios configurados del profesional |
| `GET` | `/api/citas/solicitadas` | Listar citas pendientes de aprobación |
| `PATCH` | `/api/citas/<id_cita>/estado` | Cambiar estado de una cita (aceptar/rechazar) |
| `DELETE` | `/api/citas/<id_cita>` | Cancelar cita (paciente) |
| `DELETE` | `/api/citas/profesional/<id_cita>/cancelar` | Cancelar cita (profesional) |

---

### Administración (`/api/admin/`)

#### Telemetría en tiempo real
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/admin/stats` | Estadísticas del servidor (CPU, RAM, requests) |
| `GET` | `/api/admin/stats/stream` | SSE: métricas del servidor en vivo |
| `GET` | `/api/admin/logs/stream` | SSE: logs del sistema en vivo |
| `GET` | `/api/admin/logs` | Obtener logs del sistema |

#### Usuarios
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/admin/usuarios` | Listar todos los usuarios |
| `GET` | `/api/admin/usuarios/<id_usuario>` | Obtener datos de un usuario |
| `POST` | `/api/admin/usuarios` | Crear nuevo usuario |
| `PUT` | `/api/admin/usuarios/<id_usuario>` | Editar usuario |
| `DELETE` | `/api/admin/usuarios/<id_usuario>` | Eliminar usuario |
| `PATCH` | `/api/admin/usuarios/<id_usuario>/bloquear` | Bloquear/desbloquear usuario |

#### Roles
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/admin/roles/usuarios` | Listar usuarios con sus roles |
| `PATCH` | `/api/admin/usuarios/<id_usuario>/rol` | Cambiar rol de un usuario |
| `GET` | `/api/admin/roles/historial` | Historial de cambios de rol |

#### Notificaciones
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/admin/notificaciones` | Listar notificaciones del sistema |
| `POST` | `/api/admin/notificaciones` | Crear notificación |
| `DELETE` | `/api/admin/notificaciones/<id_notificacion>` | Eliminar notificación |

#### Chatbot
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/admin/chatbot-config` | Obtener configuración del chatbot |
| `PUT` | `/api/admin/chatbot-config` | Actualizar configuración del chatbot |
| `DELETE` | `/api/admin/chatbot-config/clear-risk-terms` | Limpiar términos de riesgo del chatbot |
| `GET` | `/api/admin/chatbot-historial` | Ver historial global de conversaciones del chatbot |
| `POST` | `/api/admin/crear-columnas-diagnostico` | Migración: crear columnas de diagnóstico en BD |

---

### Tema (`/api/theme`)

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/theme` | Obtener tema activo del usuario |
| `POST` | `/api/theme` | Guardar preferencia de tema (claro/oscuro) |

---

## Instalación

### Requisitos previos

- Python 3.10+
- MySQL 8+
- Una API key de [Google AI Studio](https://aistudio.google.com/) para el chatbot

### Pasos

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
mysql -u root -p < "psyai_connect.sql"

# 6. Iniciar el servidor
python run.py
```

El servidor estará disponible en `http://127.0.0.1:5000`.

---

## Variables de entorno

| Variable | Descripción | Requerido |
|---|---|---|
| `SECRET_KEY` | Clave secreta para firmar sesiones Flask | Sí (producción) |
| `PORT` | Puerto del servidor (por defecto: `5000`) | No |
| `DB_HOST` | Host de MySQL (por defecto: `localhost`) | No |
| `DB_PORT` | Puerto de MySQL (por defecto: `3306`) | No |
| `DB_USER` | Usuario de MySQL | No |
| `DB_PASSWORD` | Contraseña de MySQL | No |
| `DB_NAME` | Nombre de la base de datos | No |
| `GEMINI_API_KEY` | API key de Google Gemini (una sola) | Para chatbot |
| `GEMINI_API_KEYS` | API keys separadas por coma (rotación automática) | Para chatbot |
| `SMTP_HOST` | Servidor SMTP para envío de correos | Para correos |
| `SMTP_PORT` | Puerto SMTP | Para correos |
| `SMTP_USER` | Usuario SMTP | Para correos |
| `SMTP_PASS` | Contraseña SMTP | Para correos |
| `SMTP_FROM` | Dirección de envío | Para correos |
| `FLASK_ENV` | Entorno (`development` / `production`) | No |
| `RATELIMIT_STORAGE_URI` | URI para almacenamiento de rate limit (Redis recomendado en prod) | No |

---

## Características principales

- **Autenticación completa**: registro, login, recuperación de contraseña por correo y reset de contraseña.
- **Chatbot de triaje con IA**: integrado con Google Gemini, con prompt del sistema configurable desde el panel admin, caché de configuración y rotación automática de API keys.
- **Chat en tiempo real**: mensajería directa entre paciente y profesional usando Server-Sent Events (SSE).
- **Gestión de citas**: creación, visualización y seguimiento de citas por parte de pacientes y profesionales.
- **Evolución del paciente**: seguimiento del progreso terapéutico visible para el paciente.
- **Telemetría en vivo**: el panel admin muestra en tiempo real el uso de CPU, RAM, disco, número de peticiones, endpoints más usados y eventos de seguridad.
- **Sistema de temas**: soporte para modo claro y oscuro persistido en localStorage.
- **Diseño responsivo**: CSS adaptativo para móvil, tablet y escritorio por cada sección.
- **Rate limiting**: protección de endpoints sensibles contra abuso.

---

## Licencia

Este proyecto es de uso educativo/interno. Revisa el repositorio para más detalles sobre su licencia.
