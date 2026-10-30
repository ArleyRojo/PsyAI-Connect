# Roles y Permisos — PsyAI Connect

> **Resumen:** Define los tres roles del sistema (`paciente`, `profesional`, `admin`), qué pantallas y funcionalidades tiene cada uno, y cómo se aplican técnicamente los permisos mediante clases DRF en `apps/core/permissions.py`.  
> **Audiencia:** Desarrolladores y QA que necesitan entender el modelo de autorización.

---

## 1. Roles del sistema

| Rol | Descripción | Modelo base | Perfil asociado |
|-----|-------------|-------------|-----------------|
| **paciente** | Usuario final que agenda citas, usa el chatbot, ve su evolución y chatea con su terapeuta | `Register(rol='paciente')` | `PerfilPaciente` (1:1) |
| **profesional** | Psicólogo que gestiona su agenda, atiende pacientes, genera reportes y sube documentos clínicos | `Register(rol='profesional')` | `PerfilProfesional` (1:1) |
| **admin** | Administrador del sistema: gestión de usuarios/roles, logs, métricas, configuración del chatbot | `Register(rol='admin')` | (sin perfil dedicado) |

> **Nota:** El campo `rol` en `Register` es un `CharField` con `choices=[('paciente','Paciente'), ('profesional','Profesional'), ('admin','Admin')]`. El usuario se autentica por email (`USERNAME_FIELD = 'email'`).

---

## 2. Pantallas por rol (templates)

Cada rol tiene su carpeta dedicada bajo `templates/`:

| Rol | Carpeta | Páginas principales |
|-----|---------|---------------------|
| **paciente** | `templates/patient/` | `patient.dashboard.html`, `chatbot.html`, `agenda-quotes.html`, `evolution.html`, `historia_clinica_paciente.html`, `facturas.html`, `mensajes.html`, `my.profile.html` |
| **profesional** | `templates/professional/` | `professional.dashboard.html`, `my.agenda.html`, `patients.html`, `patients.evolution.html`, `historia_clinica_pro.html`, `facturacion.html`, `reports.html`, `mensajes.html`, `my.profile2.html` |
| **admin** | `templates/admin/` | `admin.dashboard.html`, `admin.users.html`, `admin.roles.html`, `admin.logs.html`, `admin.notifications.html`, `admin.rendimiento.html`, `chatbot.config.html`, `facturacion.html` |

> **Compartidos:** `templates/auth/` (login, registro, recuperación), `templates/base/` (layout base, partials), `templates/legal/`, `templates/emails/`.

---

## 3. Permisos DRF — `apps/core/permissions.py`

Todas las vistas DRF usan clases de permiso que heredan de `BasePermission`. La autenticación es por sesión (`SessionAuthentication` custom).

### Clases de permiso disponibles

| Clase | Lógica | Uso típico |
|-------|--------|------------|
| `IsAuthenticatedDRF` | Usuario autenticado + cuenta activa (`activo=True`, `estadoCuenta='Activa'`) | Base para todos los endpoints privados |
| `IsPaciente` | `request.user_role == 'paciente'` | Endpoints solo para pacientes |
| `IsProfesional` | `request.user_role == 'profesional'` | Endpoints solo para profesionales |
| `IsAdmin` | `request.user_role == 'admin'` | Panel de administración |
| `IsPacienteOrProfesional` | `rol IN ('paciente','profesional')` | Endpoints compartidos (p.ej. listar profesionales) |
| `IsAdminOrProfesional` | `rol IN ('admin','profesional')` | Reportes, métricas |
| `IsOwnerOrStaff` | Dueño del recurso O `admin`/`profesional` | Objetos propios (documentos, evolución) |

### Cómo funcionan internamente

```python
# apps/core/utils.py
def get_current_user(request):
    id_usuario = request.session.get("idUsuario")
    if not id_usuario:
        return None
    return {"idUsuario": id_usuario, "rol": request.session.get("rol"), "nombre": request.session.get("nombre")}

# apps/core/permissions.py
class IsAuthenticatedDRF(BasePermission):
    def has_permission(self, request, view):
        user = get_current_user(request)
        if not user: return False
        # Verifica en BD que el usuario existe, está activo y cuenta Activa
        db_user = Register.objects.get(idUsuario=user["idUsuario"])
        return db_user.activo and db_user.estadoCuenta == "Activa"
```

> **Importante:** `request.user` de Django NO se usa (el login es manual vía `request.session`). Los permisos leen `request.session["idUsuario"]` y `request.session["rol"]`, y setean `request.user_id`, `request.user_role`, `request.user_name` para uso en vistas.

---

## 4. Matriz Rol × Funcionalidad

| Funcionalidad | Endpoint(s) | Paciente | Profesional | Admin |
|---------------|-------------|:--------:|:-----------:|:-----:|
| **Autenticación** | | | | |
| Registro | `POST /api/register` | ✅ | ✅ | ✅ |
| Login / Logout | `POST /api/login`, `/api/logout` | ✅ | ✅ | ✅ |
| Verificar email | `POST /api/verify-email` | ✅ | ✅ | — |
| Recuperar contraseña | `POST /api/forgot-password`, `/api/reset-password` | ✅ | ✅ | ✅ |
| 2FA (TOTP) | `GET/POST /api/totp/*` | ❌ | ✅ | ✅ |
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
| Enviar mensaje | `POST /api/chatbot` | ✅ | ❌ | ❌ |
| Historial chatbot | `GET/DELETE /api/chatbot` | ✅ | ❌ | ❌ |
| Configuración chatbot | `GET /api/chatbot/config` | ✅ | ❌ | ❌ (panel admin aparte) |
| **Chat directo (SSE)** | | | | |
| Contactos / Mensajes | `GET/POST /api/chat/*` | ✅ | ✅ | ✅ |
| **Evolución / Historia clínica** | | | | |
| Mi evolución | `GET/POST /api/evolucion` | ✅ | ❌ | ❌ |
| Evolución de mis pacientes | `GET /api/evolucion/profesional` | ❌ | ✅ | ✅ |
| Diagnósticos | `GET/POST /api/diagnosticos` | ❌ | ✅ | ✅ |
| Historia clínica (paciente) | `GET/POST/DELETE /api/documentos/paciente/*` | ✅ | ❌ | ✅ |
| Historia clínica (profesional) | `GET/POST/PATCH/DELETE /api/documentos/profesional/*` | ❌ | ✅ | ✅ |
| Autorizaciones de documentos | `POST /api/documentos/autorizacion/<id>` | ✅ | ✅ | ✅ |
| **Reportes** | | | | |
| Mis reportes | `GET/POST/PATCH/DELETE /api/reportes` | ❌ | ✅ | ✅ |
| Reportes eliminados | `GET /api/reportes/eliminados` | ❌ | ✅ (propios) | ✅ (todos) |
| Evolución de pacientes | `GET /api/evolucion/profesional` | ❌ | ✅ | ✅ |
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

> **Leyenda:** ✅ = acceso permitido, ❌ = denegado (403), (propias) = solo recursos donde el usuario es parte.

---

## 4. Cómo se asigna el rol

1. **Registro** (`POST /api/register`): el cliente envía `rol` en el body (`paciente` por defecto, `profesional` o `admin` si se especifica).
2. **Login** (`POST /api/login`): el cliente envía `rol` deseado; el backend verifica que el usuario tenga ese rol en BD (`usuario["rol"] == rol`).
3. **Social login** (Google): `SocialAccountAdapter` fuerza `rol = 'paciente'`.
4. **Admin** puede cambiar roles vía `PATCH /api/admin/usuarios/<id>` (`apps/admin_panel/views.py`).

---

## 5. Cómo proteger un endpoint nuevo

```python
# En tu vista
from apps.core.permissions import IsAuthenticatedDRF, IsPaciente, IsProfesional, IsAdmin

class MiVista(APIView):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]  # AND lógico
    # o
    permission_classes = [IsAuthenticatedDRF, IsPacienteOrProfesional]
```

Para lógica custom dentro de la vista:

```python
def mi_vista(request):
    user_id = getattr(request, "user_id", None)
    user_role = getattr(request, "user_role", None)
    # request.user_id, request.user_role, request.user_name los setea IsAuthenticatedDRF
```

---

## Ver también

- [`modelos-de-datos.md`](modelos-de-datos.md) — Modelos `Register`, `PerfilPaciente`, `PerfilProfesional`
- [`frontend.md`](frontend.md) — Cómo el frontend maneja el rol (sidebar, navegación)
- [`seguridad.md`](seguridad.md) — Autenticación, CSRF, 2FA, rate limiting
- [`chatbot-ia.md`](chatbot-ia.md) — Chatbot solo para pacientes
- [`pagos-facturacion.md`](pagos-facturacion.md) — Facturación por rol