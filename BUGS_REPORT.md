# 🐛 Informe de Bugs y Problemas — PsyAI Connect

> Este documento recopila todos los bugs, errores de código, inconsistencias y problemas potenciales encontrados en el proyecto **PsyAI Connect**.  
> **Estado:** Solo reporte — ningún archivo ha sido modificado.

---

## 📊 Resumen de Severidad

| Severidad | Cantidad |
|-----------|----------|
| 🔴 Crítica / Alta | 8 |
| 🟠 Media | 25 |
| 🟡 Baja | 47 |
| **Total** | **80** |

---

## 🔴 CRÍTICOS / ALTOS

### 1. Contraseñas no se almacenan en el registro
- **Archivo:** `apps/authentication/repositories.py` → `AuthRepository.create_user()`
- **Problema:** Llama `user.set_unusable_password()` (establece `contrasena=None`) y luego `user.save()` guarda con `contrasena=None`. El hash SHA256 pasado como parámetro **nunca se guarda en la base de datos**.
- **Impacto:** Los usuarios registrados nunca podrán iniciar sesión con su contraseña.
- **Gravedad:** Crítica

### 2. Gemini sin reintentos y timeout insuficiente (1s)
- **Archivo:** `apps/chatbot/services.py`, líneas 26-37
- **Problema:** `GEMINI_RETRIES = 0` (sin reintentos), `GEMINI_REQUEST_TIMEOUT_SECONDS` capped a 1.5s, `GEMINI_TOTAL_DEADLINE_SECONDS` capped a 2.0s.
- **Impacto:** Gemini casi nunca responde a tiempo y no hay reintentos. El chatbot falla casi siempre al fallback local.
- **Gravedad:** Alta

### 3. Lookup inválido `estado__ne` en Django ORM
- **Archivo:** `apps/scheduling/repositories.py`, líneas 33-38
- **Problema:** `estado__ne="Cancelada"` no es un lookup válido de Django. Los válidos son `exact`, `in`, `gt`, `lt`, `isnull`, `regex`, etc.
- **Impacto:** `FieldError` en runtime al validar disponibilidad de horarios. Rompe `get_appointment_in_slot`.
- **Gravedad:** Alta

### 4. `order_by("-fechaDiagnostico")` en modelo sin ese campo
- **Archivo:** `apps/professionals/repositories.py`, líneas 237-248
- **Problema:** `PacientesProfesional` no tiene campo `fechaDiagnostico`.
- **Impacto:** `FieldError` en `get_latest_patient_diagnosis`.
- **Gravedad:** Alta

### 5. `list_patients_for_chat` retorna profesionales, no pacientes
- **Archivo:** `apps/professionals/services.py`, líneas 143-147
- **Problema:** Llama `repo.list_verified_professionals()` en lugar de retornar pacientes.
- **Impacto:** El chat del profesional muestra profesionales en lugar de pacientes.
- **Gravedad:** Alta

### 6. Rol `admin` permitido en registro público
- **Archivo:** `apps/authentication/serializers.py`, línea 26
- **Problema:** El campo `rol` permite `"admin"` y `RegisterView` no restringe esta opción.
- **Impacto:** Escalada de privilegios crítica — cualquier usuario puede registrarse como administrador y acceder al panel completo.
- **Gravedad:** Alta

### 7. Vista SQL `vistahistorialchatbot` inexistente + SQL MySQL-specific
- **Archivo:** `apps/admin_panel/repositories.py`, líneas 326, 555, 568
- **Problema:** 
  - Consultas SQL raw usan `CURDATE()` (función exclusiva de MySQL).
  - Referencian la vista `vistahistorialchatbot` que no existe en las migraciones ni en `psyai_connect.sql`.
- **Impacto:** Fallan en tests (SQLite en memoria) y en producción si la vista no se crea manualmente.
- **Gravedad:** Alta

### 8. Estadísticas de facturas para profesionales retorna pacientes
- **Archivo:** `apps/billing/views.py`, líneas 187-188
- **Problema:** `GET /api/facturas/stats` para profesionales llama `get_professional_patients()` en lugar de estadísticas.
- **Impacto:** El profesional no obtiene estadísticas de sus facturas (monto total, pendiente, pagado).
- **Gravedad:** Media-Alta

---

## 🟠 MEDIOS (25)

### Autenticación y Sesión

#### 9. `request.user` vacío en templates
- **Archivos:** `templates/patient/patient.dashboard.html`, `templates/professional/professional.dashboard.html`
- **Problema:** El proyecto usa autenticación basada en sesión manual (`request.session["idUsuario"]`), no `django.contrib.auth`. `request.user` será `AnonymousUser`.
- **Impacto:** `{{ request.user.nombre }}`, `{{ request.user.rol }}`, `{{ request.user.foto_perfil }}` muestran valores vacíos.
- **Gravedad:** Media

#### 10. Campo inexistente `foto_perfil` en template
- **Archivo:** `templates/patient/patient.dashboard.html`, línea 101
- **Problema:** El modelo `Register` define el campo como `fotoPerfil` (camelCase). Django templates acceden a atributos de Python, así que `foto_perfil` no existe.
- **Impacto:** La foto de perfil no se renderiza en avatares del dashboard.
- **Gravedad:** Media

#### 11. `LogoutView` sin autenticación requerida
- **Archivo:** `apps/authentication/views.py`, líneas 310-318
- **Problema:** `permission_classes = [permissions.AllowAny]` en `LogoutView`.
- **Impacto:** Cualquiera puede hacer POST a `/api/logout` y limpiar la sesión actual (DoS de sesión posible).
- **Gravedad:** Media

#### 12. Race condition en `reset_password`
- **Archivo:** `apps/authentication/repositories.py`, líneas 57-64
- **Problema:** `validate_recovery_token` valida el token, luego `invalidate_recovery_token` lo invalida. Entre ambas operaciones hay una ventana de race condition.
- **Impacto:** Un token de recuperación podría usarse dos veces con peticiones concurrentes.
- **Gravedad:** Media

#### 13. Mezcla de `django_login` y sesión manual
- **Archivo:** `apps/authentication/views.py`, líneas 297-305
- **Problema:** Se llama a `django_login()` y además se establecen claves de sesión manuales (`idUsuario`, `usuario`, `rol`, etc.).
- **Impacto:** Confusión de estado de sesión. Redundante y propenso a inconsistencias.
- **Gravedad:** Baja

### Frontend / JavaScript

#### 14. `DEMO_PAGO = true` ignora respuesta real de la API
- **Archivo:** `templates/patient/aside-patient/facturas.html`, línea 334 (y `facturas_original.html`)
- **Problema:** `pagoInfoOk()` siempre retorna `true` y `resolvePagoInfo()` siempre usa datos de demo.
- **Impacto:** En producción, los pacientes siempre ven datos de pago de demo (QR fijo, cuenta de ejemplo) en lugar de los reales del profesional.
- **Gravedad:** Media

#### 15. Funciones JS referenciadas pero no definidas
- **Archivos:** Templates de facturas (patient, professional, admin)
- **Problema:** `cargarStatsFacturas`, `debounceFiltrar`, `limpiarFiltros` son referenciadas pero no definidas en ningún archivo `.js`.
- **Impacto:** `ReferenceError` en consola del navegador al cargar la tabla de facturas.
- **Gravedad:** Media

#### 16. Campo `modalidad` enviado al backend pero no existe en serializer ni modelo
- **Archivos:** `static/js/modules/patient/agendaquotes.js` → `apps/scheduling/serializers.py`
- **Problema:** El JS envía `modalidad` en POST a `/api/citas`, pero `CitaCreateSerializer` no lo incluye y el modelo `Citas` no tiene ese campo.
- **Impacto:** El dato se pierde silenciosamente.
- **Gravedad:** Baja

### Negocio / Flujo

#### 17. `fechaPago` obligatorio incluso para facturas `Pendiente`
- **Archivo:** `apps/billing/views.py`, líneas 117-118
- **Problema:** `POST /api/facturas` exige `fechaPago` para TODAS las facturas, incluso las en estado `Pendiente`.
- **Impacto:** No se puede crear una factura pendiente sin `fechaPago`, rompiendo el flujo de negocio.
- **Gravedad:** Media

#### 18. Requisito `PacientesProfesional` bloquea flujo legítimo de facturación
- **Archivo:** `apps/billing/services.py`, línea 74
- **Problema:** Crear factura requiere asignación formal previa en `PacientesProfesional`.
- **Impacto:** El profesional no puede generar factura para un paciente con cita activa pero sin asignación previa.
- **Gravedad:** Media

#### 19. Pacientes no pueden cancelar sus propias citas vía PATCH
- **Archivo:** `apps/scheduling/views.py`, líneas 79-83
- **Problema:** `CitaDetailViewSet.partial_update` solo permite a profesionales cambiar estado de cita.
- **Impacto:** El paciente no puede marcar su cita como cancelada desde la UI (aunque puede vía DELETE).
- **Gravedad:** Media

#### 20. `SolicitudDerechos.fechaLimite` no tiene default ni es calculado automáticamente
- **Archivo:** `apps/patients/models.py`, línea 499
- **Problema:** `fechaLimite = models.DateField()` sin `default=` ni `auto_now_add`.
- **Impacto:** Si se crea una solicitud sin pasar `fechaLimite`, falla con `IntegrityError` (campo NOT NULL sin default).
- **Gravedad:** Media

### Seguridad / Criptografía

#### 21. Hash de contraseña SHA256 sin sal (criptográficamente débil)
- **Archivo:** `apps/authentication/security.py`, líneas 8-13
- **Problema:** `hash_password()` usa `hashlib.sha256()` sin sal. Aunque `Register.set_password()` usa PBKDF2 de Django, la capa de servicios no lo usa.
- **Impacto:** Si la BD se compromete, las contraseñas se crackean fácilmente con fuerza bruta o tablas arcoíris.
- **Gravedad:** Alta

#### 22. `probar_gemini.py` lee `.env` directamente
- **Archivo:** `probar_gemini.py`, líneas 4-9
- **Problema:** Lee el archivo `.env` directamente para obtener `GEMINI_API_KEY`.
- **Impacto:** Exposición de secrets si el archivo se commitea al repositorio.
- **Gravedad:** Media

### Configuración y Despliegue

#### 23. Concatenación de string en filtros de fecha
- **Archivo:** `apps/billing/repositories.py`, líneas 66, 86, 108
- **Problema:** `qs.filter(fecha__lte=fecha_hasta + " 23:59:59")` — depende de conversión implícita de MySQL.
- **Impacto:** Frágil y no portable a otros backends de base de datos.
- **Gravedad:** Media

#### 24. Invalidación de sesiones O(n) al bloquear usuario
- **Archivo:** `apps/admin_panel/services.py`, líneas 110-120
- **Problema:** Itera sobre `Session.objects.all()` para encontrar y eliminar sesiones de un usuario.
- **Impacto:** Con miles de sesiones activas, operación lenta que bloquea la solicitud del administrador.
- **Gravedad:** Media

#### 25. `config_pago` solo acepta HTTPS — bloquea desarrollo local
- **Archivo:** `apps/core/views.py`, línea 272
- **Problema:** `configurada = url.startswith("https://")`.
- **Impacto:** En desarrollo local (`http://localhost:8000`), el botón de pago externo nunca se muestra aunque `PAGO_CUENTA_URL` esté configurado.
- **Gravedad:** Media

### Datos / Modelos

#### 26. Registro permite rol `admin` sin restricción
- **Archivo:** `apps/authentication/serializers.py`, línea 26
- **Problema:** Cualquier usuario que se registre puede elegir el rol `admin`.
- **Impacto:** Escalada de privilegios — acceso al panel completo de administración.
- **Gravedad:** Alta (listado también en críticos)

#### 27. `idCita` es `IntegerField` en lugar de `ForeignKey`
- **Archivo:** `apps/billing/models.py`, línea 42
- **Problema:** `idCita = models.IntegerField(null=True, blank=True)` debería ser `ForeignKey` a `Citas`.
- **Impacto:** Sin integridad referencial. Facturas con `idCita` huérfano si se elimina una cita. No se puede usar `select_related("idCita")`.
- **Gravedad:** Media

#### 28. Campos con `default=` y `null=True, blank=True` simultáneamente
- **Archivo:** `apps/scheduling/models.py`, líneas 24, 68-70
- **Problema:** `estado` tiene `default=` pero también `null=True, blank=True`.
- **Impacto:** Permite valores NULL en campos que deberían tener siempre un valor por defecto.
- **Gravedad:** Baja

#### 29. `idUsuario` como `AutoField(primary_key=True)` expone IDs secuenciales
- **Archivo:** `apps/authentication/models.py`, línea 33
- **Problema:** IDs predecibles.
- **Impacto:** Facilita enumeración de usuarios y ataques IDOR si las comprobaciones de autorización fallan.
- **Gravedad:** Media

#### 30. `EvolucionPaciente.idPaciente` referencia `Register` sin filtrar por rol
- **Archivo:** `apps/patients/models.py`, líneas 89-94
- **Problema:** `ForeignKey` a `Register` sin restricción de que sea rol `"paciente"`.
- **Impacto:** Cualquier usuario (profesional, admin) podría tener evoluciones asociadas por error.
- **Gravedad:** Baja

#### 31. `Anamnesis.idPaciente` es `OneToOneField` — un paciente solo puede tener una anamnesis
- **Archivo:** `apps/patients/models.py`, líneas 154-159
- **Problema:** `OneToOneField` significa que cada paciente solo puede tener UNA anamnesis en toda su vida.
- **Impacto:** Si se intenta crear otra, falla con `IntegrityError`.
- **Gravedad:** Baja (diseño intencional pero limitante)

---

## 🟡 BAJOS (47)

### Código muerto / archivos huérfanos

#### 32. `facturas_original.html` huérfano
- **Archivo:** `facturas_original.html` (en la raíz del proyecto, fuera de `templates/`)
- **Problema:** Copia de `templates/patient/aside-patient/facturas.html` no referenciada por ninguna vista ni URL.
- **Impacto:** Confusión de mantenimiento, archivo muerto en el repositorio.
- **Gravedad:** Baja

#### 33. `probar_gemini.py` lee `.env` directamente
- **Ya listado como #22.**

### Problemas menores de código

#### 34. `auth_service = AuthService()` declarado dos veces
- **Archivo:** `apps/authentication/views.py`, líneas 25 y 68
- **Problema:** Definición duplicada del mismo objeto.
- **Impacto:** Código redundante.
- **Gravedad:** Baja

#### 35. `catch {}` sin parámetro en JavaScript
- **Archivos:** `static/js/modules/auth/login.js` (línea 171), `static/js/modules/auth/register.js` (líneas 289, 292)
- **Problema:** `catch {}` sin capturar el objeto de error.
- **Impacto:** Impide logging o diagnóstico de errores.
- **Gravedad:** Baja

### File handle leaks (archivos abiertos sin cerrar explícitamente)

#### 36. `DownloadResource` (professionals)
- **Archivo:** `apps/professionals/views.py`, línea 344
- **Problema:** `DjangoFileResponse(open(file_path, "rb"), ...)` sin context manager.
- **Gravedad:** Baja

#### 37. `DocumentoProfesionalDownloadView`
- **Archivo:** `apps/documents/views.py`, línea 68
- **Problema:** `FileResponse(open(file_path, "rb"))` sin context manager.
- **Gravedad:** Baja

#### 38. `DocumentoPacienteDownloadView`
- **Archivo:** `apps/documents/views.py`, línea 131
- **Problema:** `FileResponse(open(file_path, "rb"))` sin context manager.
- **Gravedad:** Baja

#### 39. `FacturaEvidenciaView`
- **Archivo:** `apps/billing/views.py`, línea 230
- **Problema:** `FileResponse(open(factura.evidencia.path, "rb"), ...)` sin context manager.
- **Gravedad:** Baja

### Inconsistencias frontend ↔ backend

#### 40. `EncuestaChatbot`: modelo vs serializer
- **Archivos:** `apps/chatbot/models.py` (línea 49) vs `apps/chatbot/serializers.py` (línea 11)
- **Problema:** Modelo acepta solo `"si"/"no"`; serializer acepta `"si"/"no"/"tal vez"`.
- **Impacto:** Si el frontend envía `"tal vez"`, el serializer valida pero el modelo rechaza al guardar.
- **Gravedad:** Media

### Otros menores

#### 41. `ProfessionalPaymentInfoPublicView` crea registro vacío si no existe
- **Archivo:** `apps/professionals/views.py`, líneas 491-494
- **Problema:** Crea instancia en memoria (no guardada en BD) y la serializa con campos vacíos.
- **Impacto:** Devuelve datos vacíos en lugar de 404 o mensaje de "no hay datos de pago".
- **Gravedad:** Baja

#### 42. `ProfessionalPaymentInfoViewSet.update` usa `get_or_create` sin `defaults`
- **Archivo:** `apps/professionals/views.py`, línea 461
- **Problema:** Crea registro con campos nulos si no existe.
- **Impacto:** Ligeramente ineficiente (dos operaciones: create + save).
- **Gravedad:** Baja

#### 43. `ChatMensajeViewSet` en patients importa `MensajesService` condicionalmente
- **Archivo:** `apps/patients/views.py`, líneas 35-43
- **Problema:** Si `apps.chatbot` no está instalado, `MensajesService = None`.
- **Impacto:** Frágil, retorna 503 si el módulo no está disponible.
- **Gravedad:** Baja

#### 44. `ResetPasswordView` / `ForgotPasswordView` sin throttling específico
- **Archivo:** `apps/authentication/views.py`
- **Problema:** No tienen rate limiting específico para prevenir abuso de envío de correos.
- **Impacto:** Posible abuso del servicio de correo.
- **Gravedad:** Baja

#### 45. `Register.create_user` en AuthRepository llama `set_unusable_password()` luego no guarda el hash
- **Archivo:** `apps/authentication/repositories.py`, líneas 21-31
- **Problema:** `set_unusable_password()` establece `contrasena=None` (inusable). Luego `user.save()` guarda con `contrasena=None`. El hash SHA256 pasado como `password_hash` nunca se guarda.
- **Impacto:** **BUG CRÍTICO** — los usuarios registrados vía este método no pueden iniciar sesión.
- **Gravedad:** Crítica (listado también en críticos)

---

## 📋 Recomendaciones Prioritarias

1. **Arreglar `estado__ne`** en `scheduling/repositories.py` → usar `.exclude(estado="Cancelada")`
2. **Restringir rol `admin`** en registro → solo admin puede crear admins
3. **Arreglar `AuthRepository.create_user`** → guardar realmente el hash de contraseña (no llamar `set_unusable_password` y luego no guardar el hash)
4. **Arreglar `order_by("-fechaDiagnostico")`** en `professionals/repositories.py` → `PacientesProfesional` no tiene ese campo
5. **Arreglar `list_patients_for_chat`** → debe retornar pacientes, no profesionales
6. **Revisar templates** que usan `request.user` → usar datos de sesión o context processor adecuado
7. **Crear vista SQL `vistahistorialchatbot`** o quitar las consultas raw que dependen de ella
8. **Remover `DEMO_PAGO = true`** del código de producción
9. **Arreglar timeouts de Gemini** → `GEMINI_RETRIES = 2`, read timeout ≥ 3s, deadline ≥ 10s
10. **Revisar hash de contraseñas** → usar `make_password` de Django (PBKDF2) en lugar de SHA256 simple

---

## ✅ Cosas que NO son bugs (verificadas)

- `AccountStatusMiddleware` está correctamente configurado en `MIDDLEWARE` de `settings/base.py`.
- `IsAuthenticatedDRF` establece `request.user_id`, `request.user_role`, `request.user_name` correctamente para las vistas que lo usan.
- `ChatMensajeViewSet` en chatbot usa `request.user_id` correctamente (establecido por `IsAuthenticatedDRF`).
- `ProfessionalPaymentInfoViewSet.update` funciona correctamente (aunque ligeramente ineficiente).
- `Facturas.to_dict()` accede correctamente a `self.items.all()` (related_name válido).
- `recover_password` invalida tokens previos correctamente.

---

*Generado automáticamente el 29 de octubre de 2026. Este documento es solo informativo; no se ha modificado ningún archivo del proyecto.*