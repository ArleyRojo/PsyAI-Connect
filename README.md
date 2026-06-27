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
| **Flask-WTF** | Protección CSRF |
| **MySQL** | Base de datos relacional |
| **mysql-connector-python** | Driver de conexión a MySQL |
| **Waitress** | Servidor WSGI para producción |
| **python-dotenv** | Gestión de variables de entorno |
| **psutil** | Métricas del sistema (CPU, RAM, disco) |
| **bcrypt** | Hash seguro de contraseñas |
| **filetype** | Validación de tipo de archivos subidos |
| **resend / Brevo** | Envío de correos transaccionales |

### Inteligencia Artificial
| Tecnología | Uso |
|---|---|
| **Google Gemini API** | Chatbot de triaje psicológico para pacientes |

La integración con Gemini soporta **rotación automática de API keys** para distribuir cuota entre múltiples proyectos de Google AI Studio.

### Frontend
| Tecnología | Uso |
|---|---|
| **HTML / Jinja2 / Bootstrap 5.0.2** | Plantillas del servidor |
| **CSS personalizado** | Estilos por módulo, tema y responsividad |
| **JavaScript vanilla** | Lógica de UI por módulo (sin frameworks) |
| **SSE (Server-Sent Events)** | Actualizaciones en tiempo real en el panel admin y el chat |

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

## Estructura de carpetas y archivos

```
PsyAI-Connect/
│
├── run.py
├── setup_install.py
├── requirements.txt
├── .env.example
├── .env
├── .gitignore
├── psyai_connect_v2.sql
├── loadtest.py
├── test_evol.py
│
└── app/
    ├── __init__.py
    ├── config.py
    │
    ├── database/
    │   ├── __init__.py
    │   ├── connection.py
    │   └── migrations.py
    │
    ├── routes/
    │   ├── __init__.py
    │   ├── admin_routes.py
    │   ├── appointment_routes.py
    │   ├── auth_routes.py
    │   ├── page_routes.py
    │   ├── patient_routes.py
    │   ├── professional_routes.py
    │   └── theme_routes.py
    │
    ├── services/
    │   ├── __init__.py
    │   ├── admin_service.py
    │   ├── appointment_service.py
    │   ├── auth_service.py
    │   ├── chat_events.py
    │   ├── chatbot_config_events.py
    │   ├── chatbot_config_service.py
    │   ├── chatbot_service.py
    │   ├── documento_service.py
    │   ├── mensajes_service.py
    │   ├── patient_service.py
    │   ├── professional_service.py
    │   └── telemetry_service.py
    │
    ├── repositories/
    │   ├── __init__.py
    │   ├── admin_repository.py
    │   ├── appointment_repository.py
    │   ├── auth_repository.py
    │   ├── chat_repository.py
    │   ├── chatbot_config_repository.py
    │   ├── documento_repository.py
    │   ├── mensajes_repository.py
    │   ├── patient_repository.py
    │   ├── professional_repository.py
    │   └── security_repository.py
    │
    ├── utils/
    │   ├── __init__.py
    │   ├── auth.py
    │   ├── db.py
    │   ├── exceptions.py
    │   ├── mail.py
    │   ├── security.py
    │   ├── upload_validation.py
    │   └── validators.py
    │
    ├── templates/
    │   ├── base/
    │   │   └── index.html
    │   ├── auth/
    │   │   ├── login.html
    │   │   ├── register.html
    │   │   ├── recover.html
    │   │   └── reset-password.html
    │   ├── legal/
    │   │   ├── base_legal.html
    │   │   ├── cookies.html
    │   │   ├── privacidad.html
    │   │   └── terminos.html
    │   ├── patient/
    │   │   ├── patient.dashboard.html
    │   │   └── aside-patient/
    │   │       ├── agenda-quotes.html
    │   │       ├── chatbot.html
    │   │       ├── evolution.html
    │   │       ├── historia_clinica_paciente.html
    │   │       ├── mensajes.html
    │   │       └── my.profile.html
    │   ├── professional/
    │   │   ├── professional.dashboard.html
    │   │   └── aside-professional/
    │   │       ├── historia_clinica_pro.html
    │   │       ├── mensajes.html
    │   │       ├── my.agenda.html
    │   │       ├── my.profile2.html
    │   │       ├── patients.html
    │   │       └── reports.html
    │   └── admin/
    │       ├── admin.dashboard.html
    │       └── aside-admin/
    │           ├── chatbot.config.html
    │           ├── logs.html
    │           ├── notifications.html
    │           ├── roles.html
    │           └── users.html
    │
    ├── js/
    │   └── modules/
    │       └── patient/
    │           └── chatbot.js
    │
    └── static/
        ├── css/
        │   ├── base/
        │   │   ├── animations.css
        │   │   └── base.css
        │   ├── components/
        │   │   ├── components.css
        │   │   └── custom-alerts.css
        │   ├── layout/
        │   │   └── layout.css
        │   ├── pages/
        │   │   ├── admin.css
        │   │   ├── auth.css
        │   │   ├── historia_clinica_paciente.css
        │   │   ├── historia_clinica_pro.css
        │   │   ├── landing.css
        │   │   ├── patient.css
        │   │   └── professional.css
        │   └── themes/
        │       └── theme.css
        ├── js/
        │   ├── base/
        │   │   ├── hero-carousel.js
        │   │   ├── index.js
        │   │   ├── landing.js
        │   │   └── navbar-scroll.js
        │   ├── core/shared/
        │   │   ├── alerts.js
        │   │   ├── aside.js
        │   │   ├── localStorage-detector.js
        │   │   ├── mobile-navbar-toggle.js
        │   │   ├── nombre.usuario.js
        │   │   ├── scroll-reveal.js
        │   │   ├── theme-inline.js
        │   │   └── theme.js
        │   └── modules/
        │       ├── admin/
        │       │   ├── admin.chatbot.config.js
        │       │   ├── admin.dashboard.charts.js
        │       │   ├── admin.dashboard.js
        │       │   ├── admin.dashboard.sse.js
        │       │   ├── admin.dashboard.utils.js
        │       │   ├── admin.logs.js
        │       │   ├── admin.notifications.js
        │       │   ├── admin.rendimiento.js
        │       │   ├── admin.roles.js
        │       │   └── admin.users.js
        │       ├── auth/
        │       │   ├── auth-guard.js
        │       │   ├── auth-ui.js
        │       │   ├── login.js
        │       │   ├── logout.js
        │       │   ├── recover.js
        │       │   └── register.js
        │       ├── patient/
        │       │   ├── agendaquotes.js
        │       │   ├── aside.js
        │       │   ├── chatbot.js
        │       │   ├── evolution.js
        │       │   ├── historia_clinica_paciente.js
        │       │   └── my.profile.js
        │       ├── professional/
        │       │   ├── aside.js
        │       │   ├── historia_clinica_pro.js
        │       │   ├── my.agenda.js
        │       │   ├── my.profile2.js
        │       │   ├── patients.evolution.js
        │       │   ├── patients.js
        │       │   └── reports.js
        │       └── shared/
        │           └── direct-chat.js
        ├── responsive/
        │   ├── auth.css
        │   ├── general.css
        │   ├── index.css
        │   ├── responsive-admin.css
        │   ├── responsive-fix.css
        │   ├── responsive-patient.css
        │   └── responsive-professional.css
        ├── img/
        └── uploads/
            └── documentos/
```

---

## Descripción detallada de carpetas y archivos

### Raíz del proyecto

| Archivo | Descripción |
|---|---|
| `run.py` | Punto de entrada de la aplicación. Carga las variables de entorno, crea la app Flask con `create_app()`, inicializa la base de datos (`init_db()`), imprime en consola todas las rutas REST registradas al arrancar y lanza el servidor de desarrollo con `app.run()`. En producción se usa Waitress en lugar de este archivo. |
| `setup_install.py` | Script de instalación guiada que se ejecuta una sola vez. Crea el entorno virtual si no existe, instala las dependencias de `requirements.txt` y genera el archivo `.env` con valores iniciales (incluyendo una `SECRET_KEY` segura generada automáticamente). |
| `requirements.txt` | Lista de dependencias Python del proyecto (Flask, mysql-connector-python, bcrypt, psutil, flask-limiter, flask-wtf, resend, filetype, waitress, etc.). Se instalan con `pip install -r requirements.txt`. |
| `.env` | Variables de entorno reales con credenciales del proyecto (base de datos, API keys, SMTP). **No debe subirse a Git.** |
| `.env.example` | Plantilla de `.env` con todos los campos necesarios pero sin valores reales. Se copia y renombra a `.env` al configurar el proyecto por primera vez. |
| `.gitignore` | Define qué archivos y carpetas Git debe ignorar: `.env`, `venv/`, `__pycache__/`, archivos de subidas, etc. |
| `psyai_connect_v2.sql` | Dump completo de la base de datos MySQL. Contiene la estructura de todas las tablas y datos iniciales (usuarios de prueba, configuración del chatbot, etc.). Se importa con `mysql -u root -p < psyai_connect_v2.sql`. |
| `loadtest.py` | Script de pruebas de carga para simular múltiples peticiones concurrentes al servidor y medir el rendimiento bajo estrés. |
| `test_evol.py` | Script de pruebas específico para el módulo de evolución del paciente. |

---

### `app/` — Paquete principal de la aplicación

| Archivo | Descripción |
|---|---|
| `app/__init__.py` | Factory function `create_app()`. Instancia Flask, registra todos los blueprints (rutas), configura CORS, CSRF, rate limiter y los manejadores de error globales. Es el punto de ensamblaje de toda la aplicación. |
| `app/config.py` | Clase `Config` con toda la configuración de Flask: `SECRET_KEY`, cookie de sesión, parámetros de la base de datos, límites de subida de archivos, rate limits, CSRF y logging. También define `JSONFormatter` y `TextFormatter` para distintos formatos de log según el entorno. |

---

### `app/database/` — Conexión y esquema de base de datos

| Archivo | Descripción |
|---|---|
| `connection.py` | Gestiona el pool de conexiones MySQL usando `mysql-connector-python`. Expone `get_connection()` para obtener una conexión del pool y `close_pool()` para liberarlo al apagar la app. El tamaño del pool se configura con `DB_POOL_SIZE` en `.env`. |
| `migrations.py` | Define y ejecuta `init_db()`, que crea todas las tablas de la base de datos si no existen (`CREATE TABLE IF NOT EXISTS`). Incluye las tablas: `Register`, `PerfilPaciente`, `PerfilProfesional`, `AuditoriaAccesos`, `Login`, `Disponibilidad`, `Citas`, `ConversacionesChatbot`, `Mensajes`, `Documentos`, `Diagnosticos`, `Reportes`, `Evolucion`, `ChatbotConfig`, `ChatbotSatisfaccion` y `CambiosRol`. |

---

### `app/routes/` — Endpoints REST y rutas de páginas

Cada archivo define un Blueprint de Flask con un grupo de endpoints.

| Archivo | Descripción |
|---|---|
| `auth_routes.py` | Endpoints de autenticación: `POST /api/register`, `POST /api/login`, `POST /api/logout`, `GET /api/session`, `POST /api/forgot-password` y `POST /api/reset-password`. Incluye rate limiting por IP y registro de eventos de seguridad ante intentos fallidos. |
| `patient_routes.py` | Endpoints del portal de pacientes: gestión de perfil y foto, historial de evolución, citas, chatbot IA (enviar mensaje, historial, configuración, encuesta de satisfacción, consentimiento) y mensajería en tiempo real con el profesional. |
| `professional_routes.py` | Endpoints del portal de profesionales: perfil, disponibilidad de horarios, dashboard, lista de pacientes asignados, evolución, diagnósticos, reportes clínicos y chat con pacientes. |
| `admin_routes.py` | Endpoints del panel de administración: estadísticas del servidor en tiempo real (SSE), logs del sistema, gestión completa de usuarios (CRUD, bloqueo), cambio de roles e historial, notificaciones y configuración del chatbot de IA. |
| `appointment_routes.py` | Endpoints de citas: crear, listar, cancelar y cambiar el estado de una cita. Expone horarios disponibles y fechas con disponibilidad. |
| `page_routes.py` | Sirve las páginas HTML (Jinja2). Controla el acceso por rol: redirige a `/login.html` si el usuario no tiene el rol requerido para acceder a un dashboard. También resuelve rutas legacy que antes apuntaban a archivos estáticos. |
| `theme_routes.py` | Endpoints `GET /api/theme` y `POST /api/theme` para leer y guardar la preferencia de tema (claro/oscuro) del usuario en la base de datos. |

---

### `app/services/` — Lógica de negocio

Cada servicio orquesta las operaciones del dominio, llamando a uno o más repositorios.

| Archivo | Descripción |
|---|---|
| `auth_service.py` | Lógica de registro de usuarios (validación, hash de contraseña con bcrypt, creación de perfil según rol), login (verificación de credenciales, auditoría de accesos), logout y flujo completo de recuperación y restablecimiento de contraseña con token. |
| `patient_service.py` | Lógica de gestión del perfil del paciente: leer y actualizar datos personales, subir y actualizar la foto de perfil. |
| `professional_service.py` | Lógica del perfil del profesional: lectura, actualización, configuración de disponibilidad horaria y construcción del dashboard con estadísticas (citas pendientes, pacientes activos, próxima cita). |
| `admin_service.py` | Lógica del panel de administración: listar, crear, editar y eliminar usuarios; bloquear/desbloquear cuentas; cambiar roles con registro en historial; gestionar notificaciones del sistema. |
| `appointment_service.py` | Lógica de creación de citas con validación de disponibilidad, gestión de estados (Pendiente → Completada / Cancelada) y cancelación por parte del paciente o del profesional. |
| `chatbot_service.py` | Integración principal con la API de Google Gemini. Gestiona el envío de mensajes al modelo, construye el historial de conversación, aplica el prompt del sistema configurable y detecta palabras de riesgo. Implementa rotación automática de API keys (usando `GEMINI_API_KEYS`) y reintentos con back-off ante errores 429/5xx. |
| `chatbot_config_service.py` | Lee y actualiza la configuración del chatbot (modelo Gemini, prompt del sistema, términos de riesgo, etc.) almacenada en base de datos. Mantiene un caché en memoria con TTL de 30 segundos para evitar consultas frecuentes. |
| `chatbot_config_events.py` | Generador SSE que emite la configuración del chatbot en tiempo real a los clientes conectados cuando detecta cambios de versión. |
| `chat_events.py` | Generador SSE para el chat en tiempo real entre paciente y profesional. Mantiene un registro de clientes SSE activos y emite nuevos mensajes a los participantes de la conversación en cuanto se insertan. |
| `documento_service.py` | Gestión de documentos clínicos subidos por los profesionales: validación del tipo de archivo, almacenamiento en `static/uploads/documentos/` con nombre único (UUID) y operaciones de lectura y eliminación. |
| `mensajes_service.py` | Lógica de mensajería directa: obtener el historial de mensajes entre un paciente y su profesional, y registrar nuevos mensajes en la base de datos. |
| `telemetry_service.py` | Recolecta y expone métricas del servidor en memoria sin dependencias externas: conteo de peticiones, visitantes únicos diarios, endpoints más usados, historial de latencia, uso de CPU/RAM/disco (vía `psutil`), clientes SSE activos y eventos de seguridad (intentos fallidos de login, IPs bloqueadas). |

---

### `app/repositories/` — Acceso a datos (SQL)

Cada repositorio encapsula las consultas SQL de su dominio. Ningún servicio ejecuta SQL directamente.

| Archivo | Descripción |
|---|---|
| `auth_repository.py` | Consultas de autenticación: buscar usuario por email, crear usuario con hash de contraseña, registrar auditoría de accesos, guardar y verificar tokens de recuperación de contraseña. |
| `patient_repository.py` | Consultas del perfil del paciente: leer y actualizar `PerfilPaciente`, actualizar foto de perfil, registrar y obtener entradas de evolución, gestionar el consentimiento del chatbot. |
| `professional_repository.py` | Consultas del perfil del profesional: leer y actualizar `PerfilProfesional`, gestionar disponibilidad de horarios, obtener pacientes asignados, diagnósticos, reportes clínicos y datos del dashboard. |
| `admin_repository.py` | Consultas de administración: CRUD completo de usuarios, bloqueo de cuentas, cambio de roles con inserción en historial (`CambiosRol`), CRUD de notificaciones del sistema y consulta del historial global del chatbot. |
| `appointment_repository.py` | Consultas de citas: insertar cita en `Citas`, consultar disponibilidad, listar citas por paciente o profesional, actualizar estado y eliminar. |
| `chat_repository.py` | Consultas de mensajería directa: insertar mensajes en `Mensajes`, obtener historial de conversación entre dos usuarios y listar los contactos disponibles para chatear. |
| `chatbot_config_repository.py` | Consultas sobre la tabla `ChatbotConfig`: leer la configuración activa, actualizarla y registrar encuestas de satisfacción del chatbot. |
| `documento_repository.py` | Consultas sobre documentos clínicos: insertar referencia de documento, listar documentos de un paciente y eliminar por ID. |
| `mensajes_repository.py` | Consultas auxiliares de mensajes: insertar mensaje y recuperar historial (alternativa a `chat_repository` para contextos específicos). |
| `security_repository.py` | Consultas relacionadas con seguridad: registrar y consultar eventos de auditoría de accesos, IPs bloqueadas y tokens de recuperación. |

---

### `app/utils/` — Utilidades transversales

| Archivo | Descripción |
|---|---|
| `auth.py` | Decoradores y helpers de control de acceso. `@require_role(*roles)` protege un endpoint verificando que el usuario en sesión tenga uno de los roles indicados (devuelve 401 si no está autenticado, 403 si el rol no coincide). `require_authenticated()` y `check_role()` ofrecen validación imperativa para uso fuera de decoradores. |
| `db.py` | Context manager `get_cursor()` que obtiene una conexión del pool, crea un cursor y garantiza el cierre tanto del cursor como de la conexión al salir del bloque `with`, incluso ante excepciones. Simplifica el manejo de recursos en los repositorios. |
| `exceptions.py` | Define las excepciones personalizadas del proyecto: `ValidationError`, `AuthenticationError`, `AuthorizationError` y `DatabaseError`. Permiten distinguir el tipo de error en los servicios para devolver el código HTTP adecuado. |
| `mail.py` | Envío de correos transaccionales usando la API de **Brevo** (ex SendinBlue) vía HTTP. Implementa `send_recovery_email()` que construye un correo HTML con el enlace de restablecimiento de contraseña y lo envía al destinatario. La API key se configura con `BREVO_API_KEY` en `.env`. |
| `security.py` | Funciones criptográficas: `hash_password()` genera el hash bcrypt de una contraseña plana, `check_password()` la verifica, `generate_token()` crea tokens URL-safe seguros (usados en recuperación de contraseña) y `generate_uuid()` genera identificadores únicos para nombres de archivos subidos. |
| `upload_validation.py` | Valida los archivos subidos antes de guardarlos: verifica la extensión contra la lista `ALLOWED_UPLOAD_EXTENSIONS`, comprueba el tamaño máximo (`MAX_UPLOAD_SIZE_MB`) y usa la librería `filetype` para confirmar el tipo MIME real del archivo (evita que se suban archivos renombrados con extensión falsa). |
| `validators.py` | Funciones de validación de datos de entrada: verifica formato de email, fortaleza de contraseña, longitud de campos de texto, formato de número telefónico y que los valores de enums (como género o rol) sean válidos. |

---

### `app/templates/` — Plantillas HTML (Jinja2)

Las plantillas se organizan por rol de usuario. Los dashboards usan un layout con panel lateral (`aside`) que carga secciones de forma dinámica vía JavaScript.

#### `templates/base/`
| Archivo | Descripción |
|---|---|
| `index.html` | Landing page pública de la plataforma. Presenta el producto, sus características y llamadas a la acción para registrarse o iniciar sesión. |

#### `templates/auth/`
| Archivo | Descripción |
|---|---|
| `login.html` | Formulario de inicio de sesión. |
| `register.html` | Formulario de registro de nuevo usuario con selección de rol (paciente o profesional). |
| `recover.html` | Formulario para solicitar el correo de recuperación de contraseña ingresando el email. |
| `reset-password.html` | Formulario para establecer una nueva contraseña usando el token recibido por correo. |

#### `templates/legal/`
| Archivo | Descripción |
|---|---|
| `base_legal.html` | Plantilla base con el layout común (encabezado, navegación, pie de página) para las páginas legales. Las demás extienden esta plantilla. |
| `privacidad.html` | Política de privacidad de la plataforma. |
| `terminos.html` | Términos y condiciones de uso. |
| `cookies.html` | Política de uso de cookies. |

#### `templates/patient/`
| Archivo | Descripción |
|---|---|
| `patient.dashboard.html` | Dashboard principal del paciente. Incluye la barra de navegación lateral y el contenedor donde se cargan dinámicamente las secciones del aside. |
| `aside-patient/agenda-quotes.html` | Sección de citas del paciente: calendario de disponibilidad del profesional, formulario para agendar una nueva cita y listado de citas próximas y pasadas. |
| `aside-patient/chatbot.html` | Interfaz del chatbot de triaje psicológico impulsado por Gemini. Incluye el área de conversación, campo de texto y pantalla de consentimiento informado que el paciente debe aceptar antes de usar el chatbot. |
| `aside-patient/evolution.html` | Seguimiento de la evolución terapéutica del paciente: formulario para registrar una nueva entrada (cómo se siente hoy) y visualización del historial de entradas anteriores. |
| `aside-patient/historia_clinica_paciente.html` | Vista de la historia clínica del paciente: diagnósticos registrados por el profesional y documentos clínicos adjuntos. |
| `aside-patient/mensajes.html` | Chat en tiempo real entre el paciente y su profesional asignado, con actualización automática vía SSE. |
| `aside-patient/my.profile.html` | Perfil del paciente: foto, nombre, datos personales (género, edad, teléfono) y formulario de edición. |

#### `templates/professional/`
| Archivo | Descripción |
|---|---|
| `professional.dashboard.html` | Dashboard principal del profesional con panel lateral y resumen de métricas (pacientes activos, citas pendientes). |
| `aside-professional/my.agenda.html` | Agenda del profesional: configuración de horarios de disponibilidad y listado de citas programadas con sus pacientes. |
| `aside-professional/patients.html` | Listado de pacientes asignados al profesional con acceso al detalle de cada uno. |
| `aside-professional/historia_clinica_pro.html` | Herramienta para gestionar la historia clínica de un paciente: registrar diagnósticos y adjuntar documentos clínicos (PDF, DOCX, imágenes). |
| `aside-professional/reports.html` | Creación, edición y eliminación de reportes clínicos. Incluye una papelera de reportes eliminados. |
| `aside-professional/mensajes.html` | Chat en tiempo real entre el profesional y sus pacientes, con lista de conversaciones activas. |
| `aside-professional/my.profile2.html` | Perfil del profesional: especialidad, licencia, años de experiencia, foto y formulario de actualización. |

#### `templates/admin/`
| Archivo | Descripción |
|---|---|
| `admin.dashboard.html` | Dashboard del administrador con métricas en vivo del servidor (CPU, RAM, disco, requests/minuto, endpoints más usados) actualizadas por SSE. |
| `aside-admin/users.html` | Gestión completa de usuarios: tabla con todos los registros, formularios para crear y editar usuarios, y opción de bloquear/desbloquear o eliminar cuentas. |
| `aside-admin/roles.html` | Cambio de roles de usuarios y visualización del historial de cambios de rol con fecha y responsable. |
| `aside-admin/logs.html` | Visor de logs del sistema en tiempo real (SSE). Muestra eventos recientes de la aplicación con nivel de severidad y timestamp. |
| `aside-admin/notifications.html` | Gestión de notificaciones del sistema: crear mensajes informativos para mostrar a los usuarios y eliminar los existentes. |
| `aside-admin/chatbot.config.html` | Configuración del chatbot de IA: selección del modelo Gemini, edición del prompt del sistema, gestión de términos de riesgo y visualización del historial global de conversaciones del chatbot. |

---

### `app/js/` — Módulo JavaScript legacy

| Archivo | Descripción |
|---|---|
| `js/modules/patient/chatbot.js` | Versión original del módulo de chatbot del paciente (anterior a la refactorización a `static/js`). Puede coexistir con la versión en `static` durante la transición. |

---

### `app/static/css/` — Hojas de estilo

#### `css/base/`
| Archivo | Descripción |
|---|---|
| `animations.css` | Keyframes y clases de animación reutilizables (fade-in, slide-in, pulse, etc.) usadas en toda la aplicación. |
| `base.css` | Estilos globales: reset CSS, tipografía base, variables CSS de color y espaciado, y estilos de elementos HTML comunes. |

#### `css/components/`
| Archivo | Descripción |
|---|---|
| `components.css` | Estilos de componentes reutilizables: botones, tarjetas, badges, modales, tablas, formularios y el panel lateral (aside). |
| `custom-alerts.css` | Estilos de alertas y notificaciones tipo toast personalizadas para reemplazar los `alert()` nativos del navegador. |

#### `css/layout/`
| Archivo | Descripción |
|---|---|
| `layout.css` | Estructura general de la página: contenedor principal, grid de columnas, header, footer y posicionamiento del aside. |

#### `css/pages/`
| Archivo | Descripción |
|---|---|
| `admin.css` | Estilos exclusivos del panel de administración: gráficas de telemetría, tablas de usuarios, indicadores de métricas en vivo. |
| `auth.css` | Estilos de las páginas de autenticación (login, registro, recuperación de contraseña): fondos, tarjetas centradas, ilustraciones. |
| `historia_clinica_paciente.css` | Estilos de la vista de historia clínica del paciente: timeline de diagnósticos y visor de documentos. |
| `historia_clinica_pro.css` | Estilos del formulario de historia clínica del profesional: área de carga de documentos y listado de archivos adjuntos. |
| `landing.css` | Estilos de la landing page: secciones hero, características, llamada a la acción y footer. |
| `patient.css` | Estilos del dashboard y todas las secciones del portal del paciente: chatbot, evolución, agenda y mensajes. |
| `professional.css` | Estilos del dashboard y todas las secciones del portal del profesional: agenda, lista de pacientes y reportes. |

#### `css/themes/`
| Archivo | Descripción |
|---|---|
| `theme.css` | Define las variables CSS para el modo claro y oscuro (colores primarios, secundarios, fondos, textos, bordes). Las demás hojas de estilo usan estas variables para soportar ambos temas sin duplicar código. |

---

### `app/static/js/` — Scripts JavaScript

#### `js/base/` — Scripts de la landing page
| Archivo | Descripción |
|---|---|
| `hero-carousel.js` | Controla el carrusel de imágenes en la sección hero de la landing page (transiciones automáticas e indicadores). |
| `index.js` | Script principal de la landing: inicializa todos los módulos de la página (carrusel, scroll reveal, navbar). |
| `landing.js` | Lógica específica de la landing: animaciones de entrada de secciones, smooth scroll y efectos visuales. |
| `navbar-scroll.js` | Cambia la apariencia de la barra de navegación al hacer scroll (sombra, fondo sólido). |

#### `js/core/shared/` — Utilidades compartidas entre todos los portales
| Archivo | Descripción |
|---|---|
| `alerts.js` | Sistema de alertas tipo toast: muestra notificaciones de éxito, error o información sin interrumpir el flujo del usuario. |
| `aside.js` | Lógica genérica del panel lateral: carga de secciones de forma dinámica (fetch del HTML parcial), estado activo del ítem de menú seleccionado. |
| `localStorage-detector.js` | Detecta si `localStorage` está disponible y activo en el navegador (puede estar bloqueado en modo incógnito). |
| `mobile-navbar-toggle.js` | Maneja la apertura y cierre del menú hamburguesa en dispositivos móviles. |
| `nombre.usuario.js` | Obtiene el nombre del usuario desde la sesión (`GET /api/session`) y lo muestra en el encabezado del dashboard. |
| `scroll-reveal.js` | Aplica animaciones de aparición a elementos cuando entran en el viewport usando `IntersectionObserver`. |
| `theme-inline.js` | Se ejecuta antes del render de la página para aplicar el tema (claro/oscuro) sin parpadeo, leyendo la preferencia guardada en `localStorage`. |
| `theme.js` | Lógica completa del sistema de temas: alternancia manual, sincronización con el servidor (`POST /api/theme`) y escucha de cambios del sistema operativo. |

#### `js/modules/admin/` — Scripts del panel de administración
| Archivo | Descripción |
|---|---|
| `admin.dashboard.js` | Inicializa el dashboard del admin: coordina la carga de métricas y la conexión SSE. |
| `admin.dashboard.sse.js` | Gestiona la conexión `EventSource` con `/api/admin/stats/stream` y `/api/admin/logs/stream` para recibir telemetría y logs en tiempo real. |
| `admin.dashboard.charts.js` | Renderiza las gráficas de barras y líneas de telemetría (requests por minuto, endpoints más usados) usando la API Canvas del navegador. |
| `admin.dashboard.utils.js` | Funciones auxiliares del dashboard: formateo de bytes, cálculo de porcentajes y actualización de indicadores visuales. |
| `admin.users.js` | CRUD de usuarios desde la UI del admin: carga la tabla, abre modales de creación/edición, envía los formularios a la API y actualiza la vista. |
| `admin.roles.js` | Gestión de roles: muestra la tabla de usuarios con sus roles actuales, envía el cambio de rol a la API y recarga el historial. |
| `admin.logs.js` | Visor de logs: suscribe al SSE de logs y añade entradas al panel en tiempo real con coloreado por nivel de severidad. |
| `admin.notifications.js` | Gestión de notificaciones: lista las existentes, envía nuevas y elimina las seleccionadas. |
| `admin.chatbot.config.js` | Formulario de configuración del chatbot: carga la config actual, permite editar el prompt del sistema, los términos de riesgo y el modelo, y guarda los cambios. |
| `admin.rendimiento.js` | Muestra indicadores de rendimiento del servidor en el panel lateral (CPU, RAM, disco) actualizados periódicamente. |

#### `js/modules/auth/` — Scripts de autenticación
| Archivo | Descripción |
|---|---|
| `login.js` | Maneja el envío del formulario de login, muestra errores de validación y redirige al dashboard correspondiente según el rol del usuario. |
| `register.js` | Maneja el registro: validación en cliente, envío del formulario y redirección al login tras el éxito. |
| `recover.js` | Envía el email de recuperación y muestra la confirmación al usuario. |
| `logout.js` | Llama a `POST /api/logout`, limpia el estado local y redirige al login. |
| `auth-guard.js` | Se incluye en las páginas protegidas: verifica que haya sesión activa con `GET /api/session` y redirige al login si no la hay. |
| `auth-ui.js` | Funciones compartidas de la UI de autenticación: toggle de visibilidad de contraseña, indicador de fortaleza y mensajes de error inline. |

#### `js/modules/patient/` — Scripts del portal del paciente
| Archivo | Descripción |
|---|---|
| `chatbot.js` | Interfaz del chatbot: envía mensajes a `POST /api/chatbot/enviar`, renderiza las respuestas del modelo, maneja el estado de carga y suscribe al SSE de configuración para actualizar el comportamiento sin recargar la página. |
| `agendaquotes.js` | Agenda de citas del paciente: carga el calendario de disponibilidad del profesional, envía solicitudes de cita y lista las citas pasadas y próximas. |
| `evolution.js` | Módulo de evolución: formulario de nueva entrada diaria y carga del historial de entradas anteriores. |
| `historia_clinica_paciente.js` | Carga los diagnósticos y documentos del paciente desde la API y los renderiza en la vista de historia clínica. |
| `my.profile.js` | Gestiona el formulario de perfil del paciente: carga los datos actuales, maneja la subida de foto y envía actualizaciones. |
| `aside.js` | Control del panel lateral del paciente: navegación entre secciones y estado activo del menú. |

#### `js/modules/professional/` — Scripts del portal del profesional
| Archivo | Descripción |
|---|---|
| `my.agenda.js` | Gestión de la agenda: configuración de horarios de disponibilidad, visualización del calendario y listado de citas. |
| `patients.js` | Lista de pacientes asignados: carga desde la API, búsqueda y acceso al detalle de cada paciente. |
| `patients.evolution.js` | Vista de evolución de los pacientes del profesional: gráficas de progreso y entradas de diario de cada paciente. |
| `historia_clinica_pro.js` | Formulario de historia clínica: registro de diagnósticos y subida de documentos clínicos con validación de tipo y tamaño. |
| `reports.js` | CRUD de reportes clínicos: crear, editar, eliminar y restaurar desde la papelera. |
| `my.profile2.js` | Perfil del profesional: carga datos, maneja la foto de perfil y envía actualizaciones de especialidad, licencia y experiencia. |
| `aside.js` | Control del panel lateral del profesional. |

#### `js/modules/shared/` — Scripts compartidos entre roles
| Archivo | Descripción |
|---|---|
| `direct-chat.js` | Módulo de chat en tiempo real compartido entre paciente y profesional: suscribe al SSE de mensajes, renderiza el historial y envía nuevos mensajes a la API. |

---

### `app/static/responsive/` — CSS responsivo

Hojas de estilo que adaptan el diseño a pantallas pequeñas (móvil y tablet) para cada sección.

| Archivo | Descripción |
|---|---|
| `general.css` | Ajustes responsivos globales aplicables en toda la aplicación. |
| `index.css` | Responsividad de la landing page. |
| `auth.css` | Responsividad de las páginas de login, registro y recuperación. |
| `responsive-admin.css` | Responsividad del panel de administración. |
| `responsive-patient.css` | Responsividad del portal del paciente. |
| `responsive-professional.css` | Responsividad del portal del profesional. |
| `responsive-fix.css` | Correcciones puntuales de responsividad para casos específicos de navegadores o dispositivos. |

---

### `app/static/img/` — Imágenes del proyecto

Imágenes usadas en la interfaz: logo de la plataforma (`Logo.jpg`, `Logo.webp`), imágenes de portada para la landing page (`Psicologia.jpg`, `Psicologia2.png`, `psicologia1.jpg` y sus variantes `.webp` optimizadas para la web) y el `favicon.ico`.

### `app/static/uploads/` — Archivos subidos por usuarios

Carpeta donde se almacenan los archivos que los usuarios suben en tiempo de ejecución: fotos de perfil (en la raíz de `uploads/`) y documentos clínicos PDF y DOCX (en `uploads/documentos/`). Los archivos se guardan con nombres UUID para evitar colisiones y exposición de información. Esta carpeta **no debe subirse a Git** (está en `.gitignore`).

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
| `POST` | `/api/chat/enviar` | Enviar mensaje al profesional |

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

### Opción 1: Instalación automática (recomendada)

```bash
python setup_install.py
```

El script crea el entorno virtual, instala las dependencias y genera el `.env` automáticamente.

### Opción 2: Instalación manual

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
mysql -u root -p < psyai_connect_v2.sql

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
| `DB_POOL_SIZE` | Tamaño del pool de conexiones (por defecto: `10`) | No |
| `GEMINI_API_KEY` | API key de Google Gemini (una sola) | Para chatbot |
| `GEMINI_API_KEYS` | API keys separadas por coma (rotación automática) | Para chatbot |
| `BREVO_API_KEY` | API key de Brevo para correos transaccionales | Para correos |
| `BREVO_FROM` | Dirección de envío verificada en Brevo | Para correos |
| `BREVO_FROM_NAME` | Nombre del remitente | Para correos |
| `FLASK_ENV` | Entorno (`development` / `production`) | No |
| `FLASK_DEBUG` | Activar modo debug (`1` / `0`) | No |
| `RATELIMIT_STORAGE_URI` | URI para rate limit (Redis recomendado en prod) | No |
| `LOGIN_RATE_LIMIT` | Límite para `POST /api/login` | No |
| `REGISTER_RATE_LIMIT` | Límite para `POST /api/register` | No |
| `PASSWORD_RECOVERY_RATE_LIMIT` | Límite para recuperar/restablecer contraseña | No |
| `MAX_UPLOAD_SIZE_MB` | Tamaño máximo de archivos subidos en MB (por defecto: `5`) | No |
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
