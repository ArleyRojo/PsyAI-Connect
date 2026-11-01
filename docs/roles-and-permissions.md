# Roles y Permisos — PsyAI Connect

> **Resumen:** Define los tres roles del sistema (`paciente`, `profesional`, `admin`), qué pantallas y funcionalidades tiene cada uno, cómo se asignan los roles al registrarse o iniciar sesión, y cómo se protegen los endpoints mediante clases DRF en `apps/core/permissions.py` y utilidades en `apps/core/utils.py`.  
> **Audiencia:** desarrolladores y QA que necesitan entender el modelo de autorización.

---

## 1. Roles del sistema

El modelo de usuario es `Register` (`apps/authentication/models.py`), que extiende `AbstractBaseUser` con `USERNAME_FIELD = 'email'`. Cada usuario tiene un campo `rol` y opcionalmente un perfil asociado 1:1.

| Rol | Descripción | Modelo base | Perfil asociado | `is_staff` / `is_superuser` |
|-----|-------------|-------------|-----------------|------------------------------|
| **paciente** | Usuario final: agenda citas, usa el chatbot, ve su evolución, chatea con su profesional y gestiona sus facturas | `Register(rol='paciente')` | `PerfilPaciente` (1:1) | `False` / `False` |
| **profesional** | Psicólogo: gestiona agenda, atiende pacientes asignados, genera reportes, sube documentos clínicos y usa 2FA opcional | `Register(rol='profesional')` | `PerfilProfesional` (1:1) | `False` / `False` |
| **admin** | Administrador del sistema: gestiona usuarios, roles, logs, métricas, configuración del chatbot y notificaciones | `Register(rol='admin')` | (sin perfil dedicado) | `True` / `True` |

### Detalles del modelo `Register`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `idUsuario` | AutoField (PK) | Identificador del usuario |
| `nombre` | CharField(120) | Nombre completo |
| `email` | EmailField (único) | Usuario de autenticación (`USERNAME_FIELD`) |
| `password` | CharField(255) | Hash bcrypt (columna `contrasena`) |
| `rol` | CharField(20) | `choices=[('paciente','Paciente'), ('profesional','Profesional'), ('admin','Admin')]` |
| `fotoPerfil` | CharField(255) | URL de foto de perfil |
| `estadoCuenta` | CharField(20) | `choices=[('Activa','Activa'), ('Suspendida','Suspendida')]`, default `Activa` |
| `activo` | BooleanField | default `True` |
| `email_verificado` | BooleanField | default `False` |
| `fechaRegistro` | DateTimeField | auto_now_add |

> **Nota importante:** La autenticación es **basada en sesión**, no usa `request.user` de Django por defecto. Los permisos leen `request.session["idUsuario"]`, `request.session["rol"]` y `request.session["nombre"]`, y setean `request.user_id`, `request.user_role`, `request.user_name` para uso en vistas.

---

## 2. Pantallas por rol (templates)

Cada rol tiene su carpeta dedicada bajo `templates/`:

| Rol | Carpeta | Páginas principales |
|-----|---------|---------------------|
| **paciente** | `templates/patient/` | `patient.dashboard.html`, `aside-patient/chatbot.html`, `aside-patient/agenda-quotes.html`, `aside-patient/evolution.html`, `aside-patient/historia_clinica_paciente.html`, `aside-patient/facturas.html`, `aside-patient/mensajes.html`, `aside-patient/my.profile.html` |
| **profesional** | `templates/professional/` | `professional.dashboard.html`, `aside-professional/my.agenda.html`, `aside-professional/patients.html`, `aside-professional/patients.evolution.html`, `aside-professional/historia_clinica_pro.html`, `aside-professional/facturacion.html`, `aside-professional/reports.html`, `aside-professional/mensajes.html`, `aside-professional/my.profile2.html` |
| **admin** | `templates/admin/` | `admin.dashboard.html`, `aside-admin/users.html`, `aside-admin/roles.html`, `aside-admin/logs.html`, `aside-admin/notifications.html`, `aside-admin/rendimiento.html`, `aside-admin/chatbot.config.html`, `aside-admin/facturacion.html` |

> **Compartidos:** `templates/auth/` (login, registro, recuperación, 2FA), `templates/base/` (layout base, partials `head.html`, `scripts.html`), `templates/legal/` (términos, privacidad, cookies), `templates/emails/` (plantillas de correo), `templates/socialaccount/` (login/registro con Google).

---

## 3. Permisos DRF — `apps/core/permissions.py`

Todas las vistas de Django REST Framework usan clases de permiso que heredan de `BasePermission`. El acceso se evalúa con lógica AND: todas las clases en `permission_classes` deben retornar `True`.

### Utilidades de autenticación (`apps/core/utils.py`)

| Función | Descripción |
|---------|-------------|
| `AuthHelper.get_current_user(request)` | Lee `idUsuario`, `rol` y `nombre` de `request.session`. Retorna `None` si no hay sesión. |
| `AuthHelper.require_auth(request)` | Valida que exista sesión, que el usuario exista en BD, que esté `activo=True` y `estadoCuenta='Activa'`. Retorna 401/403 si falla. |
| `AuthHelper.require_role(request, *roles)` | Igual que `require_auth` más verifica que el `rol` esté en la lista permitida. Retorna 403 si no coincide. |

### Clases de permiso disponibles

| Clase | Lógica | Uso típico |
|-------|--------|------------|
| `IsAuthenticatedDRF` | Intenta `request.user` (DRF/token); fallback a `get_current_user(request)`. Valida `activo` y `estadoCuenta='Activa'` en BD. Setea `request.user_id`, `request.user_role`, `request.user_name`. | Base para todos los endpoints privados |
| `IsPaciente` | `request.user_role == 'paciente'` | Endpoints solo pacientes (chatbot, evolución propia, citas propias) |
| `IsProfesional` | `request.user_role == 'profesional'` | Endpoints solo profesionales (disponibilidad, diagnósticos, reportes propios) |
| `IsAdmin` | `request.user_role == 'admin'` | Panel de administración (usuarios, roles, logs, métricas, config chatbot) |
| `IsPacienteOrProfesional` | `rol IN ('paciente','profesional')` | Endpoints compartidos (listar profesionales, contacto) |
| `IsAdminOrProfesional` | `rol IN ('admin','profesional')` | Reportes, métricas, disponibilidad |
| `IsOwnerOrStaff` | `has_permission`: rol no es None; `has_object_permission`: admin/profesional o dueño del objeto (`obj.idUsuario == request.user_id`) | Objetos propios (documentos, evolución, citas) |

### Flujo interno de `IsAuthenticatedDRF`

1. Intenta autenticación por DRF (`request.user.is_authenticated`): si existe, busca el `Register` por `idUsuario`/`pk`, valida `activo` y `estadoCuenta`, setea atributos en `request`.
2. Si no hay usuario DRF, fallback a sesión: `get_current_user(request)` lee `idUsuario`, `rol`, `nombre` de `request.session`.
3. Busca el `Register` en BD por `idUsuario`.
4. Rechaza si `activo=False` o `estadoCuenta != 'Activa'` (limpia la sesión con `request.session.flush()`).
5. Setea `request.user_id`, `request.user_role` (normalizado a minúsculas), `request.user_name`.

---

## 4. Matriz Rol × Funcionalidad

| Funcionalidad | Endpoint(s) | Paciente | Profesional | Admin |
|---------------|-------------|:--------:|:-----------:|:-----:|
| **Autenticación** | | | | |
| Registro | `POST /api/register` | ✅ | ✅ | ✅ |
| Login / Logout | `POST /api/login`, `/api/logout` | ✅ | ✅ | ✅ |
| Verificar email | `POST /api/verify-email` | ✅ | ✅ | — |
| Recuperar contraseña | `POST /api/forgot-password`, `/api/reset-password` | ✅ | ✅ | ✅ |
| 2FA setup / confirm / disable / status | `POST/GET /api/totp/*` | ❌ | ✅ | ✅ |
| 2FA verify login | `POST /api/totp/verify-login` | ✅ | ✅ | ✅ |
| **Perfil** | | | | |
| Ver/editar propio perfil | `GET/PUT /api/perfil/paciente`, `/api/perfil/profesional` | ✅ | ✅ | ✅ (propio) |
| Subir foto | `PUT /api/perfil/paciente/foto`, `/api/perfil/profesional/foto` | ✅ | ✅ | ✅ |
| **Agenda / Citas** | | | | |
| Ver disponibilidad pública | `GET /api/citas/disponibles`, `/fechas-disponibles` | ✅ | ✅ | ✅ |
| Crear cita | `POST /api/citas` | ✅ | ✅ | ❌ |
| Listar mis citas | `GET /api/citas` | ✅ | ✅ | ✅ |
| Actualizar estado cita | `PATCH /api/citas/<id>` | ❌ | ✅ | ✅ |
| Cancelar cita | `DELETE /api/citas/<id>` | ✅ | ✅ | ✅ |
| Disponibilidad (crear/ver) | `POST/GET /api/disponibilidad` | ❌ | ✅ | ✅ |
| Próxima cita | `GET /api/citas/proxima` | ✅ | ❌ | ❌ |
| **Chatbot IA** | | | | |
| Enviar mensaje | `POST /api/chatbot/enviar` | ✅ | ❌ | ❌ |
| Historial chatbot | `GET/DELETE /api/chatbot`, `/api/chatbot/historial` | ✅ | ❌ | ❌ |
| Configuración chatbot | `GET /api/chatbot/config` | ✅ | ❌ | ❌ (panel admin aparte) |
| Config SSE | `GET /api/chatbot/config/events` | ✅ | ❌ | ❌ |
| **Chat directo (paciente–profesional)** | | | | |
| Contactos con mensajes | `GET /api/chat/contactos` | ✅ | ✅ | ✅ |
| Listar mensajes | `GET /api/chat/mensajes` | ✅ | ✅ | ✅ |
| Enviar mensaje | `POST /api/chat/mensajes`, `/chat/enviar` | ✅ | ✅ | ✅ |
| Borrar historial | `DELETE /api/chat/historial` | ✅ | ✅ | ✅ |
| **Evolución / Historia clínica** | | | | |
| Mi evolución | `GET/POST /api/evolucion` | ✅ | ❌ | ❌ |
| Evolución de mis pacientes | `GET /api/evolucion/profesional` | ❌ | ✅ | ✅ |
| Diagnósticos | `GET/POST /api/diagnosticos` | ❌ | ✅ | ✅ |
| Historia clínica (paciente) | `GET/POST/DELETE /api/documentos/paciente/*` | ✅ | ❌ | ✅ |
| Historia clínica (profesional) | `GET/POST/PATCH/DELETE /api/documentos/profesional/*` | ❌ | ✅ | ✅ |
| Autorización de documentos | `POST /api/documentos/autorizacion/<id>` | ✅ | ✅ | ✅ |
| **Consentimiento chatbot** | `GET/POST /paciente/consentimiento-chatbot` | ✅ | ❌ | ❌ |
| **Encuesta chatbot** | `POST /api/chatbot/encuesta` | ✅ | ❌ | ❌ |
| **Reportes** | | | | |
| Mis reportes | `GET/POST/PATCH/DELETE /api/reportes` | ❌ | ✅ | ✅ |
| Reportes eliminados | `GET /api/reportes/eliminados` | ❌ | ✅ (propios) | ✅ (todos) |
| **Facturación** | | | | |
| Listar/crear facturas | `GET/POST /api/facturas` | ✅ (propias) | ✅ (propias) | ✅ (todas) |
| Detalle/Anular factura | `GET/PATCH/DELETE /api/facturas/<id>` | ✅ (propias) | ✅ (propias) | ✅ |
| Iniciar pago Wompi | `POST /api/facturas/<id>/iniciar-pago` | ✅ (propias) | ❌ | ❌ |
| Confirmar pago (frontend) | `POST /api/facturas/<id>/confirmar-pago` | ✅ | ❌ | ❌ |
| Webhook Wompi | `POST /api/webhooks/wompi` | (público) | — | — |
| Stats facturación | `GET /api/facturas/stats` | ❌ | ✅ (propias) | ✅ (todas) |
| **Panel Admin** | | | | |
| Usuarios (listar/crear/editar/borrar) | `/api/admin/usuarios*` | ❌ | ❌ | ✅ |
| Roles | `/api/admin/roles*` | ❌ | ❌ | ✅ |
| Logs / Auditoría | `/api/admin/logs`, `/actividad` | ❌ | ❌ | ✅ |
| Métricas servidor | `/api/admin/stats`, `/usuarios-online` | ❌ | ❌ | ✅ |
| Configuración chatbot | `GET/POST /api/admin/chatbot/*` | ❌ | ❌ | ✅ |
| Notificaciones | `/api/admin/notificaciones*` | ❌ | ❌ | ✅ |

> **Leyenda:** ✅ = acceso permitido, ❌ = denegado (403), (propias) = solo recursos donde el usuario es parte (verificado por `IsOwnerOrStaff` o lógica en la vista), (público) = sin autenticación requerida.

---

## 5. Asignación de roles

| Paso | Momento | Cómo se asigna el rol |
|------|---------|----------------------|
| Registro | `POST /api/register` | El cliente envía `rol` en el body. Default: `paciente`. Valores permitidos: `paciente`, `profesional`, `admin`. |
| Login | `POST /api/login` | El cliente envía `rol` deseado. El backend verifica que `usuario["rol"] == rol` solicitado; de lo contrario rechaza. |
| Superuser | `createsuperuser` / `Register.objects.create_superuser` | Fuerza `rol='admin'`; si se intenta otro rol lanza `ValueError`. |
| Social login (Google) | `SocialAccountAdapter` | Fuerza `rol='paciente'` independientemente de lo que envíe el proveedor. |
| Cambio por admin | `PATCH /api/admin/usuarios/<id>` | Solo `admin` puede modificar el rol de cualquier usuario (`apps/admin_panel/views.py`). |
| 2FA obligatorio | `AuthService.require_totp_for_role(rol)` | Retorna `True` para `admin` y `profesional`; `False` para `paciente`. |

### Restricciones por rol en registro

- **Email verificado:** obligatorio para `profesional`, opcional para `paciente` (`EmailVerificationToken`).
- **2FA (TOTP):** opcional pero requerido para `admin` y `profesional` según `require_totp_for_role`.
- **Perfil:** `PerfilPaciente` o `PerfilProfesional` se crea automáticamente tras el registro según el rol.

---

## 6. Cómo proteger un endpoint nuevo

### Opción A: clases de permiso (recomendado)

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.permissions import (
    IsAuthenticatedDRF,
    IsPaciente,
    IsProfesional,
    IsAdmin,
    IsPacienteOrProfesional,
    IsAdminOrProfesional,
    IsOwnerOrStaff,
)

# Solo pacientes
class MiVistaPaciente(APIView):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

# Profesionales o admin
class MiVistaProAdmin(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdminOrProfesional]

# Dueño del objeto o staff
class MiVistaObjeto(APIView):
    permission_classes = [IsAuthenticatedDRF, IsOwnerOrStaff]

    def get_object(self, pk):
        obj = get_object_or_404(Modelo, pk=pk)
        self.check_object_permissions(self.request, obj)
        return obj
```

DRF evalúa las clases con lógica AND: todas deben retornar `True`.

### Opción B: utilidad `require_role` (vistas no-DRF / función)

```python
from django.http import JsonResponse
from apps.core.utils import require_role

def mi_vista(request):
    user, err = require_role(request, "paciente", "profesional")
    if err:
        return err  # JsonResponse 401 / 403
    user_id = user["idUsuario"]
    user_rol = user["rol"]
    # lógica de negocio
    return JsonResponse({"success": True})
```

### Opción C: atributos seteados por `IsAuthenticatedDRF`

Dentro de cualquier vista (DRF o no) después de pasar el permiso:

```python
user_id   = getattr(request, "user_id", None)
user_role = getattr(request, "user_role", None)  # 'paciente' | 'profesional' | 'admin'
user_name = getattr(request, "user_name", None)
```

---

## 7. Autenticación y estado de cuenta

| Concepto | Implementación |
|----------|---------------|
| Usuario de login | `email` (`USERNAME_FIELD = 'email'`) |
| Contraseña | Hash bcrypt (`SecurityHelper.hash_password`, `SecurityHelper.verify_password`) |
| Sesión | `request.session` con `idUsuario`, `rol`, `nombre`, `email`, `fotoPerfil` |
| Cuenta activa | `activo=True` y `estadoCuenta='Activa'` verificadas en cada petición |
| Cuenta suspendida | `estadoCuenta='Suspendida'` → 403 en cualquier endpoint protegido; sesión limpiada |
| Intentos fallidos | Modelo `IntentosFallidos` (bloqueo por email tras umbral) |
| Verificación email | `EmailVerificationToken` obligatorio para `profesional`, opcional para `paciente` |
| 2FA | Modelo `TOTPDevice` (RFC 6238). Obligatorio para `admin` y `profesional`. Endpoints: setup, confirm, disable, status, verify-login. |

---

## 8. Ver también

- [`data-models.md`](data-models.md) — Modelos `Register`, `PerfilPaciente`, `PerfilProfesional`, `TOTPDevice`, `EmailVerificationToken`, `IntentosFallidos`
- [`frontend.md`](frontend.md) — Cómo el frontend maneja el rol (sidebar, navegación, menús por rol)
- [`security.md`](security.md) — Autenticación, CSRF, 2FA, rate limiting, cookies seguras
- [`chatbot-ai.md`](chatbot-ai.md) — Chatbot solo para pacientes; configuración accesible por admin
- [`deployment.md`](deployment.md) — Variables de entorno y despliegue (no afecta al modelo de roles)

---

## English Version

# Roles and Permissions — PsyAI Connect

> **Summary:** Defines the three system roles (`paciente`, `profesional`, `admin`), what screens and functionalities each has, how roles are assigned at registration or login, and how endpoints are protected through DRF classes in `apps/core/permissions.py` and utilities in `apps/core/utils.py`.  
> **Audience:** developers and QA who need to understand the authorization model.

---

## 1. System roles / Roles del sistema

The user model is `Register` (`apps/authentication/models.py`), extending `AbstractBaseUser` with `USERNAME_FIELD = 'email'`. Each user has a `rol` field and optionally an associated 1:1 profile.

| Role | Description | Base model | Associated profile | `is_staff` / `is_superuser` |
|------|-------------|------------|-------------------|------------------------------|
| **paciente** | End user: schedules appointments, uses chatbot, views evolution, chats with therapist, manages invoices | `Register(rol='paciente')` | `PerfilPaciente` (1:1) | `False` / `False` |
| **profesional** | Psychologist: manages agenda, attends assigned patients, generates reports, uploads clinical documents, optional 2FA | `Register(rol='profesional')` | `PerfilProfesional` (1:1) | `False` / `False` |
| **admin** | System administrator: manages users/roles, logs, metrics, chatbot configuration and notifications | `Register(rol='admin')` | (no dedicated profile) | `True` / `True` |

### `Register` model details

| Field | Type | Description |
|-------|------|-------------|
| `idUsuario` | AutoField (PK) | User identifier |
| `nombre` | CharField(120) | Full name |
| `email` | EmailField (unique) | Authentication username (`USERNAME_FIELD`) |
| `password` | CharField(255) | bcrypt hash (column `contrasena`) |
| `rol` | CharField(20) | `choices=[('paciente','Paciente'), ('profesional','Profesional'), ('admin','Admin')]` |
| `fotoPerfil` | CharField(255) | Profile picture URL |
| `estadoCuenta` | CharField(20) | `choices=[('Activa','Activa'), ('Suspendida','Suspendida')]`, default `Activa` |
| `activo` | BooleanField | default `True` |
| `email_verificado` | BooleanField | default `False` |
| `fechaRegistro` | DateTimeField | auto_now_add |

> **Important:** Authentication is **session-based**, not exclusively using Django's `request.user`. Permissions read `request.session["idUsuario"]`, `request.session["rol"]` and `request.session["nombre"]`, and set `request.user_id`, `request.user_role`, `request.user_name` for use in views.

---

## 2. Screens by role (templates) / Pantallas por rol (templates)

Each role has its own folder under `templates/`:

| Role | Folder | Main pages |
|------|--------|------------|
| **paciente** | `templates/patient/` | `patient.dashboard.html`, `aside-patient/chatbot.html`, `aside-patient/agenda-quotes.html`, `aside-patient/evolution.html`, `aside-patient/historia_clinica_paciente.html`, `aside-patient/facturas.html`, `aside-patient/mensajes.html`, `aside-patient/my.profile.html` |
| **profesional** | `templates/professional/` | `professional.dashboard.html`, `aside-professional/my.agenda.html`, `aside-professional/patients.html`, `aside-professional/patients.evolution.html`, `aside-professional/historia_clinica_pro.html`, `aside-professional/facturacion.html`, `aside-professional/reports.html`, `aside-professional/mensajes.html`, `aside-professional/my.profile2.html` |
| **admin** | `templates/admin/` | `admin.dashboard.html`, `aside-admin/users.html`, `aside-admin/roles.html`, `aside-admin/logs.html`, `aside-admin/notifications.html`, `aside-admin/rendimiento.html`, `aside-admin/chatbot.config.html`, `aside-admin/facturacion.html` |

> **Shared:** `templates/auth/` (login, registration, recovery), `templates/base/` (base layout, partials), `templates/legal/`, `templates/emails/`.

---

## 3. DRF permissions — `apps/core/permissions.py` / Permisos DRF

All DRF views use permission classes inheriting from `BasePermission`. Access is evaluated with AND logic: all classes in `permission_classes` must return `True`.

### Authentication utilities (`apps/core/utils.py`)

| Function | Description |
|---------|-------------|
| `AuthHelper.get_current_user(request)` | Reads `idUsuario`, `rol` and `nombre` from `request.session`. Returns `None` if no session. |
| `AuthHelper.require_auth(request)` | Validates session exists, user exists in DB, `activo=True` and `estadoCuenta='Activa'`. Returns 401/403 if fails. |
| `AuthHelper.require_role(request, *roles)` | Same as `require_auth` plus verifies `rol` is in allowed list. Returns 403 if no match. |

### Available permission classes

| Class | Logic | Typical use |
|-------|-------|-------------|
| `IsAuthenticatedDRF` | Tries `request.user` (DRF/token); fallback to session. Validates `activo` and `estadoCuenta='Activa'` in DB. Sets `request.user_id`, `request.user_role`, `request.user_name`. | Base for all private endpoints |
| `IsPaciente` | `request.user_role == 'paciente'` | Patient-only endpoints |
| `IsProfesional` | `request.user_role == 'profesional'` | Professional-only endpoints |
| `IsAdmin` | `request.user_role == 'admin'` | Admin panel |
| `IsPacienteOrProfesional` | `rol IN ('paciente','profesional')` | Shared endpoints |
| `IsAdminOrProfesional` | `rol IN ('admin','profesional')` | Reports, metrics |
| `IsOwnerOrStaff` | Owner of resource OR `admin`/`profesional` | Own objects (documents, evolution) |

### Internal flow of `IsAuthenticatedDRF`

1. Tries DRF authentication (`request.user.is_authenticated`).
2. If exists, searches `Register` by `idUsuario`/`pk`, validates `activo` and `estadoCuenta`, sets attributes on `request`.
3. If no DRF user, fallback to session: `get_current_user(request)` reads `idUsuario`, `rol`, `nombre` from `request.session`.
4. Searches `Register` in DB by `idUsuario`.
5. Rejects if `activo=False` or `estadoCuenta != 'Activa'` (clears session with `request.session.flush()`).
6. Sets `request.user_id`, `request.user_role` (lowercase), `request.user_name`.

---

## 4. Role × Functionality matrix / Matriz Rol × Funcionalidad

| Functionality | Endpoint(s) | Patient | Professional | Admin |
|---------------|-------------|:--------:|:-----------:|:-----:|
| **Authentication** | | | | |
| Registration | `POST /api/register` | ✅ | ✅ | ✅ |
| Login / Logout | `POST /api/login`, `/api/logout` | ✅ | ✅ | ✅ |
| Email verification | `POST /api/verify-email` | ✅ | ✅ | — |
| Password recovery | `POST /api/forgot-password`, `/api/reset-password` | ✅ | ✅ | ✅ |
| 2FA (TOTP) | `GET/POST /api/totp/*` | ❌ | ✅ | ✅ |
| **Profile** | | | | |
| View/edit own profile | `GET/PUT /api/perfil/paciente`, `/api/perfil/profesional` | ✅ | ✅ | ✅ (own) |
| Upload photo | `PUT /api/perfil/paciente/foto`, `/api/perfil/profesional/foto` | ✅ | ✅ | ✅ |
| **Appointments** | | | | |
| View public availability | `GET /api/citas/disponibles`, `/fechas-disponibles` | ✅ | ✅ | ✅ |
| Create appointment | `POST /api/citas` | ✅ | ✅ | ❌ |
| List my appointments | `GET /api/citas` | ✅ | ✅ | ✅ |
| Update appointment status | `PATCH /api/citas/<id>` | ❌ | ✅ | ✅ |
| Cancel appointment | `DELETE /api/citas/<id>` | ✅ | ✅ | ✅ |
| Availability (create/view) | `POST/GET /api/disponibilidad` | ❌ | ✅ | ✅ |
| Next appointment | `GET /api/citas/proxima` | ✅ | ❌ | ❌ |
| **AI Chatbot** | | | | |
| Send message | `POST /api/chatbot/enviar` | ✅ | ❌ | ❌ |
| Chatbot history | `GET/DELETE /api/chatbot`, `/api/chatbot/historial` | ✅ | ❌ | ❌ |
| Chatbot config | `GET /api/chatbot/config` | ✅ | ❌ | ❌ (admin panel separate) |
| **Direct chat (SSE)** | | | | |
| Contacts / Messages | `GET/POST /api/chat/*` | ✅ | ✅ | ✅ |
| **Evolution / Clinical history** | | | | |
| My evolution | `GET/POST /api/evolucion` | ✅ | ❌ | ❌ |
| Evolution of my patients | `GET /api/evolucion/profesional` | ❌ | ✅ | ✅ |
| Diagnoses | `GET/POST /api/diagnosticos` | ❌ | ✅ | ✅ |
| Clinical history (patient) | `GET/POST/DELETE /api/documentos/paciente/*` | ✅ | ❌ | ✅ |
| Clinical history (professional) | `GET/POST/PATCH/DELETE /api/documentos/profesional/*` | ❌ | ✅ | ✅ |
| Document authorizations | `POST /api/documentos/autorizacion/<id>` | ✅ | ✅ | ✅ |
| **Reports** | | | | |
| My reports | `GET/POST/PATCH/DELETE /api/reportes` | ❌ | ✅ | ✅ |
| Deleted reports | `GET /api/reportes/eliminados` | ❌ | ✅ (own) | ✅ (all) |
| Patient evolution | `GET /api/evolucion/profesional` | ❌ | ✅ | ✅ |
| **Billing** | | | | |
| List/create invoices | `GET/POST /api/facturas` | ✅ (own) | ✅ (own) | ✅ (all) |
| Detail/void invoice | `GET/PATCH/DELETE /api/facturas/<id>` | ✅ (own) | ✅ (own) | ✅ |
| Start Wompi payment | `POST /api/facturas/<id>/iniciar-pago` | ✅ (own) | ❌ | ❌ |
| Confirm payment (frontend) | `POST /api/facturas/<id>/confirmar-pago` | ✅ | ❌ | ❌ |
| Wompi webhook | `POST /api/webhooks/wompi` | (public) | — | — |
| Billing stats | `GET /api/facturas/stats` | ❌ | ✅ (own) | ✅ (all) |
| **Admin Panel** | | | | |
| Users (list/create/edit/delete) | `/api/admin/usuarios*` | ❌ | ❌ | ✅ |
| Roles | `/api/admin/roles*` | ❌ | ❌ | ✅ |
| Logs / Audit | `/api/admin/logs`, `/actividad` | ❌ | ❌ | ✅ |
| Server metrics | `/api/admin/stats`, `/usuarios-online` | ❌ | ❌ | ✅ |
| Chatbot config | `GET/POST /api/admin/chatbot/*` | ❌ | ❌ | ✅ |
| Notifications | `/api/admin/notificaciones*` | ❌ | ❌ | ✅ |

> **Legend:** ✅ = access allowed, ❌ = denied (403), (own) = only resources where user is a participant, (public) = no authentication required.

---

## 5. Role assignment / Asignación de roles

| Step | Moment | How role is assigned |
|------|--------|---------------------|
| Registration | `POST /api/register` | Client sends `rol` in body. Default: `paciente`. Allowed: `paciente`, `profesional`, `admin`. |
| Login | `POST /api/login` | Client sends desired `rol`; backend verifies user has that role in BD (`usuario["rol"] == rol`). |
| Superuser | `createsuperuser` / `create_superuser` | Forces `rol='admin'`; if another role attempted raises `ValueError`. |
| Social login (Google) | `SocialAccountAdapter` | Forces `rol='paciente'` regardless of provider. |
| Admin change | `PATCH /api/admin/usuarios/<id>` | Only `admin` can modify any user's role (`apps/admin_panel/views.py`). |
| Mandatory 2FA | `AuthService.require_totp_for_role(rol)` | Returns `True` for `admin` and `profesional`; `False` for `paciente`. |

### Role restrictions in registration

- **Email verified:** mandatory for `profesional`, optional for `paciente` (`EmailVerificationToken`).
- **2FA (TOTP):** optional but required for `admin` and `profesional` per `require_totp_for_role`.
- **Profile:** `PerfilPaciente` or `PerfilProfesional` created automatically after registration according to role.

---

## 6. How to protect a new endpoint / Cómo proteger un endpoint nuevo

### Option A: permission classes (recommended)

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.permissions import (
    IsAuthenticatedDRF,
    IsPaciente,
    IsProfesional,
    IsAdmin,
    IsPacienteOrProfesional,
    IsAdminOrProfesional,
    IsOwnerOrStaff,
)

# Patients only
class MiVistaPaciente(APIView):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

# Professionals or admin
class MiVistaProAdmin(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdminOrProfesional]

# Object owner or staff
class MiVistaObjeto(APIView):
    permission_classes = [IsAuthenticatedDRF, IsOwnerOrStaff]

    def get_object(self, pk):
        obj = get_object_or_404(Modelo, pk=pk)
        self.check_object_permissions(self.request, obj)
        return obj
```

DRF evaluates classes with AND logic: all must return `True`.

### Option B: `require_role` utility (non-DRF / function views)

```python
from django.http import JsonResponse
from apps.core.utils import require_role

def mi_vista(request):
    user, err = require_role(request, "paciente", "profesional")
    if err:
        return err  # JsonResponse 401 / 403
    user_id = user["idUsuario"]
    user_rol = user["rol"]
    # business logic
    return JsonResponse({"success": True})
```

### Option C: attributes set by `IsAuthenticatedDRF`

Inside any view (DRF or not) after passing the permission:

```python
user_id   = getattr(request, "user_id", None)
user_role = getattr(request, "user_role", None)  # 'paciente' | 'profesional' | 'admin'
user_name = getattr(request, "user_name", None)
```

---

## 7. Authentication and account status / Autenticación y estado de cuenta

| Concept | Implementation |
|---------|---------------|
| Login user | `email` (`USERNAME_FIELD = 'email'`) |
| Password | bcrypt hash (`SecurityHelper.hash_password`, `SecurityHelper.verify_password`) |
| Session | `request.session` with `idUsuario`, `rol`, `nombre`, `email`, `fotoPerfil` |
| Active account | `activo=True` and `estadoCuenta='Activa'` verified on each request |
| Suspended account | `estadoCuenta='Suspendida'` → 403 on any protected endpoint; session cleared |
| Failed attempts | `IntentosFallidos` model (email blocking after threshold) |
| Email verification | `EmailVerificationToken` mandatory for `profesional`, optional for `paciente` |
| 2FA | `TOTPDevice` model (RFC 6238). Mandatory for `admin` and `profesional`. Endpoints: setup, confirm, disable, status, verify-login. |

---

## See also / Ver también

- [`data-models.md`](data-models.md) — Models `Register`, `PerfilPaciente`, `PerfilProfesional`, `TOTPDevice`, `EmailVerificationToken`, `IntentosFallidos`
- [`frontend.md`](frontend.md) — How frontend handles role (sidebar, navigation, role menus)
- [`security.md`](security.md) — Authentication, CSRF, 2FA, rate limiting, secure cookies
- [`chatbot-ai.md`](chatbot-ai.md) — Chatbot only for patients; config accessible by admin
- [`despliegue.md`](deployment.md) — Environment variables and deployment (does not affect role model)
