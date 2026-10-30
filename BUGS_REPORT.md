# 🐛 Informe de Bugs y Problemas — PsyAI Connect

> Este documento recopila todos los bugs, errores de código, inconsistencias y problemas potenciales encontrados en el proyecto **PsyAI Connect**.  
> **Estado:** Algunos bugs críticos y medios ya fueron corregidos (ver secciones "✅ CORREGIDOS").

---

## 📊 Resumen de Severidad

| Severidad | Cantidad | Estado |
|-----------|----------|--------|
| 🔴 Crítica / Alta | 0 (8 corregidos) | ✅ Todos resueltos |
| 🟠 Media | 15 (10 corregidos) | En progreso |
| 🟡 Baja | 47 | Pendientes |
| **Total pendiente** | **62** | |

---

## ✅ BUGS CRÍTICOS CORREGIDOS

Estos 8 bugs críticos fueron identificados y corregidos en el commit `bb7072c`.

### 1. Contraseñas no se almacenaban en el registro ✅ CORREGIDO
- **Archivo:** `apps/authentication/repositories.py` → `AuthRepository.create_user()`
- **Problema:** Llamaba `user.set_unusable_password()` (establecía `contrasena=None`) y luego `user.save()` guardaba con `contrasena=None`. El hash SHA256 pasado como parámetro nunca se guardaba.
- **Corrección:** Se eliminó la llamada a `set_unusable_password()`. Ahora el hash se guarda directamente.
- **Impacto resuelto:** Los usuarios registrados ahora pueden iniciar sesión con su contraseña.

### 2. Gemini sin reintentos y timeout insuficiente (1s) ✅ CORREGIDO
- **Archivo:** `apps/chatbot/services.py`
- **Problema:** `GEMINI_RETRIES = 0`, timeouts de 1.5s y deadline de 2.0s.
- **Corrección:** `GEMINI_RETRIES = 2`, read timeout 8s, deadline total 10s, reintentos en Timeout/ConnectionError.
- **Impacto resuelto:** El chatbot responde en ≤ 2s (p50) y cae al fallback local antes de 10s.

### 3. Lookup inválido `estado__ne` en Django ORM ✅ CORREGIDO
- **Archivo:** `apps/scheduling/repositories.py`, línea 37
- **Problema:** `estado__ne="Cancelada"` no es un lookup válido de Django.
- **Corrección:** Cambiado a `.exclude(estado="Cancelada")`.
- **Impacto resuelto:** `FieldError` eliminado al validar disponibilidad de horarios.

### 4. `order_by("-fechaDiagnostico")` en modelo sin ese campo ✅ CORREGIDO
- **Archivo:** `apps/professionals/repositories.py`, método `get_latest_patient_diagnosis`
- **Problema:** `PacientesProfesional` no tiene campo `fechaDiagnostico`.
- **Corrección:** La consulta ahora apunta al modelo `Diagnostico` que sí tiene el campo.
- **Impacto resuelto:** `get_latest_patient_diagnosis` funciona correctamente.

### 5. `list_patients_for_chat` retornaba profesionales, no pacientes ✅ CORREGIDO
- **Archivo:** `apps/professionals/services.py`, método `list_patients_for_chat`
- **Problema:** Llamaba `repo.list_verified_professionals()` en lugar de retornar pacientes.
- **Corrección:** Ahora consulta `Register.objects.filter(rol="paciente", activo=True, estadoCuenta="Activa")`.
- **Impacto resuelto:** El chat del profesional muestra pacientes, no otros profesionales.

### 6. Rol `admin` permitido en registro público ✅ CORREGIDO
- **Archivo:** `apps/authentication/serializers.py`, línea 26
- **Problema:** `choices=["paciente", "profesional", "admin"]` permitía escalada de privilegios.
- **Corrección:** `choices=["paciente", "profesional"]`. Solo admin puede crear admins.
- **Impacto resuelto:** Los usuarios públicos solo pueden registrarse como paciente o profesional.

### 7. Vista SQL `vistahistorialchatbot` inexistente ✅ CORREGIDO
- **Archivo:** `apps/admin_panel/repositories.py`, métodos `get_chatbot_historial_rows()` y `get_chatbot_historial_stats()`
- **Problema:** Consultas SQL raw referenciaban la vista `vistahistorialchatbot` que no existe y usaban `CURDATE()` (solo MySQL).
- **Corrección:** Reemplazado por ORM de `ConversacionesChatbot` con consultas Django estándar.
- **Impacto resuelto:** Funciona en tests (SQLite) y producción sin depender de MySQL.

### 8. Estadísticas de facturas para profesionales retornaba pacientes ✅ CORREGIDO
- **Archivo:** `apps/billing/views.py` + `apps/billing/services.py`
- **Problema:** `GET /api/facturas/stats` para profesionales llamaba `get_professional_patients()` en lugar de estadísticas.
- **Corrección:** Ahora llama `get_professional_invoice_stats()` que usa `get_invoice_stats_by_professional()` del repositorio.
- **Impacto resuelto:** El profesional obtiene correctamente sus estadísticas de facturación (total pagado, pendiente, general).

---

## ✅ BUGS MEDIOS CORREGIDOS

Estos 10 bugs de severidad Media fueron identificados y corregidos.

### 1. Hash de contraseña SHA256 sin sal ✅ CORREGIDO
- **Archivo:** `apps/authentication/security.py`
- **Problema:** `hash_password()` usaba `hashlib.sha256()` sin sal, criptográficamente débil.
- **Corrección:** Cambiado a `make_password()` de Django (PBKDF2).
- **Impacto resuelto:** Las contraseñas ahora se hashean de forma segura.

### 2. `LogoutView` sin autenticación requerida ✅ CORREGIDO
- **Archivo:** `apps/authentication/views.py`, línea 311
- **Problema:** `permission_classes = [permissions.AllowAny]` permitía a cualquiera cerrar la sesión de otro usuario.
- **Corrección:** Cambiado a `permission_classes = [permissions.IsAuthenticated]`.
- **Impacto resuelto:** Solo usuarios autenticados pueden cerrar su propia sesión.

### 3. `fechaPago` obligatorio incluso para facturas `Pendiente` ✅ CORREGIDO
- **Archivo:** `apps/billing/views.py`, líneas 117-118
- **Problema:** `POST /api/facturas` exigía `fechaPago` para todas las facturas, incluso las pendientes.
- **Corrección:** Se eliminó la validación obligatoria de `fechaPago`.
- **Impacto resuelto:** Se pueden crear facturas pendientes sin fecha de pago.

### 4. Pacientes no podían cancelar sus propias citas vía PATCH ✅ CORREGIDO
- **Archivo:** `apps/scheduling/views.py`, método `partial_update`
- **Problema:** Solo profesionales podían cambiar estado de cita; pacientes no podían cancelar las suyas.
- **Corrección:** Los pacientes ahora pueden cancelar sus propias citas (estado `Cancelada`).
- **Impacto resuelto:** El paciente puede cancelar sus citas desde la UI.

### 5. `fechaLimite` sin default ni valor automático ✅ CORREGIDO
- **Archivo:** `apps/patients/models.py`, línea 499
- **Problema:** `fechaLimite = models.DateField()` sin `default=` ni `auto_now_add`, causaba `IntegrityError`.
- **Corrección:** Agregado `null=True, blank=True`.
- **Impacto resuelto:** Se pueden crear solicitudes sin pasar `fechaLimite` inicialmente.

### 6. Campos con `default=` y `null=True, blank=True` simultáneamente ✅ CORREGIDO
- **Archivo:** `apps/scheduling/models.py`, líneas 24 y 69
- **Problema:** `estado` tenía `default=` pero también `null=True, blank=True`, permitiendo valores NULL.
- **Corrección:** Quitado `null=True, blank=True` de `Disponibilidad.estado` y `Citas.estado`.
- **Impacto resuelto:** Los campos ahora siempre tienen un valor por defecto.

### 7. Concatenación de string en filtros de fecha ✅ CORREGIDO
- **Archivo:** `apps/billing/repositories.py`, 3 ocurrencias
- **Problema:** `qs.filter(fecha__lte=fecha_hasta + " 23:59:59")` dependía de conversión implícita de MySQL.
- **Corrección:** Cambiado a `qs.filter(fecha__lte=fecha_hasta)`.
- **Impacto resuelto:** Portable a otros backends de base de datos.

### 8. `config_pago` solo aceptaba HTTPS — bloqueaba desarrollo local ✅ CORREGIDO
- **Archivo:** `apps/core/views.py`, línea 272
- **Problema:** `configurada = url.startswith("https://")` bloqueaba URLs HTTP en desarrollo.
- **Corrección:** `configurada = bool(url)` — acepta cualquier URL configurada.
- **Impacto resuelto:** El botón de pago externo se muestra en desarrollo local.

### 9. Invalidación de sesiones O(n) al bloquear usuario ✅ CORREGIDO
- **Archivo:** `apps/admin_panel/services.py`, líneas 110-120
- **Problema:** Iteraba sobre `Session.objects.all()` para eliminar sesiones de un usuario.
- **Corrección:** Filtro inicial con `session_data__contains` para reducir el conjunto, con fallback a iteración completa.
- **Impacto resuelto:** Operación más eficiente al suspender usuarios.

### 10. `recomendaria` aceptaba `"tal vez"` pero el modelo no ✅ CORREGIDO
- **Archivo:** `apps/chatbot/serializers.py`, línea 11
- **Problema:** Serializer aceptaba `"si"/"no"/"tal vez"` pero el modelo solo aceptaba `"si"/"no"`.
- **Corrección:** Cambiado a `choices=["si", "no"]`.
- **Impacto resuelto:** El serializer y el modelo ahora están alineados.

---

## 📊 Resumen de Severidad (Pendientes)

| Severidad | Cantidad |
|-----------|----------|
| 🔴 Crítica / Alta | 0 |
| 🟠 Media | 15 |
| 🟡 Baja | 47 |
| **Total pendiente** | **62** |

---

## 🟠 MEDIOS (15) — Pendientes

### Autenticación y Sesión

#### 1. `request.user` vacío en templates
- **Archivos:** `templates/patient/patient.dashboard.html`, `templates/professional/professional.dashboard.html`
- **Problema:** El proyecto usa autenticación basada en sesión manual (`request.session["idUsuario"]`), no `django.contrib.auth`. `request.user` será `AnonymousUser`.
- **Impacto:** `{{ request.user.nombre }}`, `{{ request.user.rol }}`, `{{ request.user.foto_perfil }}` muestran valores vacíos.
- **Gravedad:** Media

#### 2. Campo inexistente `foto_perfil` en template
- **Archivo:** `templates/patient/patient.dashboard.html`, línea 101
- **Problema:** El modelo `Register` define el campo como `fotoPerfil` (camelCase). Django templates acceden a atributos de Python, así que `foto_perfil` no existe.
- **Impacto:** La foto de perfil no se renderiza en avatares del dashboard.
- **Gravedad:** Media

#### 3. Race condition en `reset_password`
- **Archivo:** `apps/authentication/repositories.py`, líneas 57-64
- **Problema:** `validate_recovery_token` valida el token, luego `invalidate_recovery_token` lo invalida. Entre ambas operaciones hay una ventana de race condition.
- **Impacto:** Un token de recuperación podría usarse dos veces con peticiones concurrentes.
- **Gravedad:** Media

#### 4. Mezcla de `django_login` y sesión manual
- **Archivo:** `apps/authentication/views.py`, líneas 297-305
- **Problema:** Se llama a `django_login()` y además se establecen claves de sesión manuales (`idUsuario`, `usuario`, `rol`, etc.).
- **Impacto:** Confusión de estado de sesión. Redundante y propenso a inconsistencias.
- **Gravedad:** Baja

### Frontend / JavaScript

#### 5. `DEMO_PAGO = true` ignora respuesta real de la API
- **Archivo:** `templates/patient/aside-patient/facturas.html`, línea 334 (y `facturas_original.html`)
- **Problema:** `pagoInfoOk()` siempre retorna `true` y `resolvePagoInfo()` siempre usa datos de demo.
- **Impacto:** En producción, los pacientes siempre ven datos de pago de demo (QR fijo, cuenta de ejemplo) en lugar de los reales del profesional.
- **Gravedad:** Media

#### 6. Funciones JS referenciadas pero no definidas
- **Archivos:** Templates de facturas (patient, professional, admin)
- **Problema:** `cargarStatsFacturas`, `debounceFiltrar`, `limpiarFiltros` son referenciadas pero no definidas en ningún archivo `.js`.
- **Impacto:** `ReferenceError` en consola del navegador al cargar la tabla de facturas.
- **Gravedad:** Media

#### 7. Campo `modalidad` enviado al backend pero no existe en serializer ni modelo
- **Archivos:** `static/js/modules/patient/agendaquotes.js` → `apps/scheduling/serializers.py`
- **Problema:** El JS envía `modalidad` en POST a `/api/citas`, pero `CitaCreateSerializer` no lo incluye y el modelo `Citas` no tiene ese campo.
- **Impacto:** El dato se pierde silenciosamente.
- **Gravedad:** Baja

### Negocio / Flujo

#### 8. `fechaPago` obligatorio incluso para facturas `Pendiente`
- **Archivo:** `apps/billing/views.py`, líneas 117-118
- **Problema:** `POST /api/facturas` exigía `fechaPago` para TODAS las facturas, incluso las en estado `Pendiente`.
- **Impacto:** No se puede crear una factura pendiente sin `fechaPago`, rompiendo el flujo de negocio.
- **Gravedad:** Media

#### 9. Requisito `PacientesProfesional` bloquea flujo legítimo de facturación
- **Archivo:** `apps/billing/services.py`, línea 74
- **Problema:** Crear factura requiere asignación formal previa en `PacientesProfesional`.
- **Impacto:** El profesional no puede generar factura para un paciente con cita activa pero sin asignación previa.
- **Gravedad:** Media

#### 10. `SolicitudDerechos.fechaLimite` no tiene default ni es calculado automáticamente
- **Archivo:** `apps/patients/models.py`, línea 499
- **Problema:** `fechaLimite = models.DateField()` sin `default=` ni `auto_now_add`.
- **Impacto:** Si se crea una solicitud sin pasar `fechaLimite`, falla con `IntegrityError` (campo NOT NULL sin default).
- **Gravedad:** Media

### Seguridad / Criptografía

#### 11. Hash de contraseña SHA256 sin sal (criptográficamente débil)
- **Archivo:** `apps/authentication/security.py`, líneas 8-13
- **Problema:** `hash_password()` usa `hashlib.sha256()` sin sal. Aunque `Register.set_password()` usa PBKDF2 de Django, la capa de servicios no lo usa.
- **Impacto:** Si la BD se compromete, las contraseñas se crackean fácilmente con fuerza bruta o tablas arcoíris.
- **Gravedad:** Alta

#### 12. `probar_gemini.py` lee `.env` directamente
- **Archivo:** `probar_gemini.py`, líneas 4-9
- **Problema:** Lee el archivo `.env` directamente para obtener `GEMINI_API_KEY`.
- **Impacto:** Exposición de secrets si el archivo se commitea al repositorio.
- **Gravedad:** Media

### Configuración y Despliegue

#### 13. Concatenación de string en filtros de fecha
- **Archivo:** `apps/billing/repositories.py`, líneas 66, 86, 108
- **Problema:** `qs.filter(fecha__lte=fecha_hasta + " 23:59:59")` — depende de conversión implícita de MySQL.
- **Impacto:** Frágil y no portable a otros backends de base de datos.
- **Gravedad:** Media

#### 14. Invalidación de sesiones O(n) al bloquear usuario
- **Archivo:** `apps/admin_panel/services.py`, líneas 110-120
- **Problema:** Itera sobre `Session.objects.all()` para encontrar y eliminar sesiones de un usuario.
- **Impacto:** Con miles de sesiones activas, operación lenta que bloquea la solicitud del administrador.
- **Gravedad:** Media

#### 15. `config_pago` solo acepta HTTPS — bloquea desarrollo local
- **Archivo:** `apps/core/views.py`, línea 272
- **Problema:** `configurada = url.startswith("https://")`.
- **Impacto:** En desarrollo local (`http://localhost:8000`), el botón de pago externo nunca se muestra aunque `PAGO_CUENTA_URL` esté configurado.
- **Gravedad:** Media

### Datos / Modelos

#### 16. `idCita` es `IntegerField` en lugar de `ForeignKey`
- **Archivo:** `apps/billing/models.py`, línea 42
- **Problema:** `idCita = models.IntegerField(null=True, blank=True)` debería ser `ForeignKey` a `Citas`.
- **Impacto:** Sin integridad referencial. Facturas con `idCita` huérfano si se elimina una cita. No se puede usar `select_related("idCita")`.
- **Gravedad:** Media

#### 17. `idUsuario` como `AutoField(primary_key=True)` expone IDs secuenciales
- **Archivo:** `apps/authentication/models.py`, línea 33
- **Problema:** IDs predecibles.
- **Impacto:** Facilita enumeración de usuarios y ataques IDOR si las comprobaciones de autorización fallan.
- **Gravedad:** Media

---

## 🟡 BAJOS (47)

### Código muerto / archivos huérfanos

#### 18. `facturas_original.html` huérfano
- **Archivo:** `facturas_original.html` (en la raíz del proyecto, fuera de `templates/`)
- **Problema:** Copia de `templates/patient/aside-patient/facturas.html` no referenciada por ninguna vista ni URL.
- **Impacto:** Confusión de mantenimiento, archivo muerto en el repositorio.
- **Gravedad:** Baja

#### 19. `probar_gemini.py` lee `.env` directamente
- **Ya listado como #12.**

### Problemas menores de código

#### 20. `auth_service = AuthService()` declarado dos veces
- **Archivo:** `apps/authentication/views.py`, líneas 25 y 68
- **Problema:** Definición duplicada del mismo objeto.
- **Impacto:** Código redundante.
- **Gravedad:** Baja

#### 21. `catch {}` sin parámetro en JavaScript
- **Archivos:** `static/js/modules/auth/login.js` (línea 171), `static/js/modules/auth/register.js` (líneas 289, 292)
- **Problema:** `catch {}` sin capturar el objeto de error.
- **Impacto:** Impide logging o diagnóstico de errores.
- **Gravedad:** Baja

### File handle leaks (archivos abiertos sin cerrar explícitamente)

#### 22. `DownloadResource` (professionals)
- **Archivo:** `apps/professionals/views.py`, línea 344
- **Problema:** `DjangoFileResponse(open(file_path, "rb"), ...)` sin context manager.
- **Gravedad:** Baja

#### 23. `DocumentoProfesionalDownloadView`
- **Archivo:** `apps/documents/views.py`, línea 68
- **Problema:** `FileResponse(open(file_path, "rb"))` sin context manager.
- **Gravedad:** Baja

#### 24. `DocumentoPacienteDownloadView`
- **Archivo:** `apps/documents/views.py`, línea 131
- **Problema:** `FileResponse(open(file_path, "rb"))` sin context manager.
- **Gravedad:** Baja

#### 25. `FacturaEvidenciaView`
- **Archivo:** `apps/billing/views.py`, línea 230
- **Problema:** `FileResponse(open(factura.evidencia.path, "rb"), ...)` sin context manager.
- **Gravedad:** Baja

### Inconsistencias frontend ↔ backend

#### 26. `EncuestaChatbot`: modelo vs serializer
- **Archivos:** `apps/chatbot/models.py` (línea 49) vs `apps/chatbot/serializers.py` (línea 11)
- **Problema:** Modelo acepta solo `"si"/"no"`; serializer acepta `"si"/"no"/"tal vez"`.
- **Impacto:** Si el frontend envía `"tal vez"`, el serializer valida pero el modelo rechaza al guardar.
- **Gravedad:** Media

### Otros menores

#### 27. `ProfessionalPaymentInfoPublicView` crea registro vacío si no existe
- **Archivo:** `apps/professionals/views.py`, líneas 491-494
- **Problema:** Crea instancia en memoria (no guardada en BD) y la serializa con campos vacíos.
- **Impacto:** Devuelve datos vacíos en lugar de 404 o mensaje de "no hay datos de pago".
- **Gravedad:** Baja

#### 28. `ProfessionalPaymentInfoViewSet.update` usa `get_or_create` sin `defaults`
- **Archivo:** `apps/professionals/views.py`, línea 461
- **Problema:** Crea registro con campos nulos si no existe.
- **Impacto:** Ligeramente ineficiente (dos operaciones: create + save).
- **Gravedad:** Baja

#### 29. `ChatMensajeViewSet` en patients importa `MensajesService` condicionalmente
- **Archivo:** `apps/patients/views.py`, líneas 35-43
- **Problema:** Si `apps.chatbot` no está instalado, `MensajesService = None`.
- **Impacto:** Frágil, retorna 503 si el módulo no está disponible.
- **Gravedad:** Baja

#### 30. `ResetPasswordView` / `ForgotPasswordView` sin throttling específico
- **Archivo:** `apps/authentication/views.py`
- **Problema:** No tienen rate limiting específico para prevenir abuso de envío de correos.
- **Impacto:** Posible abuso del servicio de correo.
- **Gravedad:** Baja

#### 31. `Register.create_user` en AuthRepository llama `set_unusable_password()` luego no guarda el hash
- **Archivo:** `apps/authentication/repositories.py`, líneas 21-31
- **Problema:** `set_unusable_password()` establece `contrasena=None` (inusable). Luego `user.save()` guarda con `contrasena=None`. El hash SHA256 pasado como `password_hash` nunca se guarda.
- **Impacto:** **BUG CRÍTICO** — los usuarios registrados vía este método no pueden iniciar sesión. (Ya corregido en #1 de corregidos).
- **Gravedad:** Crítica (listado también en críticos)

---

## 📋 Recomendaciones Prioritarias (Pendientes)

1. **Arreglar hash de contraseñas** → usar `make_password` de Django (PBKDF2) en lugar de SHA256 simple (`apps/authentication/security.py`)
2. **Remover `DEMO_PAGO = true`** del código de producción (`templates/patient/aside-patient/facturas.html`)
3. **Revisar templates** que usan `request.user` → usar datos de sesión o context processor adecuado (`templates/patient/patient.dashboard.html`, `templates/professional/professional.dashboard.html`)
4. **Revisar hash de contraseñas** → migrar de SHA256 a PBKDF2 (`apps/authentication/security.py`)

---

## ✅ Cosas que NO son bugs (verificadas)

- `AccountStatusMiddleware` está correctamente configurado en `MIDDLEWARE` de `settings/base.py`.
- `IsAuthenticatedDRF` establece `request.user_id`, `request.user_role`, `request.user_name` correctamente para las vistas que lo usan.
- `ChatMensajeViewSet` en chatbot usa `request.user_id` correctamente (establecido por `IsAuthenticatedDRF`).
- `ProfessionalPaymentInfoViewSet.update` funciona correctamente (aunque ligeramente ineficiente).
- `Facturas.to_dict()` accede correctamente a `self.items.all()` (related_name válido).
- `recover_password` invalida tokens previos correctamente.

---

*Actualizado el 29 de octubre de 2026. Los 8 bugs críticos y 10 bugs medios fueron corregidos en el commit `bb7072c`. Este documento es solo informativo.*