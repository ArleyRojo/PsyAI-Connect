# Documentación de Seguridad — PsyAI Connect

> **Versión:** 1.1  
> **Fecha:** 29 de octubre de 2026  
> **Audiencia:** Desarrolladores, auditores de seguridad, equipo de operaciones.  
> **Estado:** Documento activo. Refleja el estado real del código fuente en `config/settings/`, `apps/authentication/`, `apps/core/` y `apps/chatbot/`.

---

## Tabla de contenido

1. [Resumen de severidad](#resumen-de-severidad)
2. [Capas de seguridad implementadas](#capas-de-seguridad-implementadas)
   - 2.1. Autenticación y gestión de sesión
   - 2.2. Autorización y control de acceso basado en roles (RBAC)
   - 2.3. Middleware de seguridad y cabeceras HTTP
   - 2.4. Validación y sanitización de entrada
   - 2.5. Rate limiting y protección contra fuerza bruta
   - 2.6. Seguridad de sesión y cookies
   - 2.7. Sanitización de datos sensibles (PII)
   - 2.8. Almacenamiento de contraseñas (Argon2id / SHA-256 legacy)
   - 2.9. Verificación de dos factores (TOTP / 2FA)
   - 2.10. Verificación de correo electrónico
   - 2.11. Rate limiting por endpoint de autenticación
   - 2.12. Middleware de estado de cuenta
   - 2.13. Validación de archivos subidos
   - 2.14. Webhooks con firma HMAC (pagos Wompi)
   - 2.15. CSP y cabeceras de seguridad adicionales
3. [Flujo de login y migración de contraseñas](#flujo-de-login-y-migración-de-contraseñas)
4. [Recomendaciones prioritarias (pendientes)](#recomendaciones-prioritarias-pendientes)
5. [Cosas que NO son bugs (verificadas)](#cosas-que-no-son-bugs-verificadas)
6. [Checklist de despliegue a producción](#checklist-de-despliegue-a-producción)

---

## Resumen de severidad

| Severidad | Cantidad | Estado |
|-----------|----------|--------|
| 🔴 Crítica / Alta | 0 (8 corregidos) | ✅ Todos resueltos |
| 🟠 Media | 15 (10 corregidos) | En progreso |
| 🟡 Baja | 47 | Pendientes |
| **Total pendiente** | **62** | |

Los 8 bugs críticos y 10 bugs de severidad media fueron corregidos en el commit `bc833e4`. Los 15 restantes de severidad media y los 47 de severidad baja quedan pendientes para próximas entregas.

---

## Capas de seguridad implementadas

A continuación se detallan las capas de seguridad del proyecto, organizadas por capa defensiva. Cada entrada indica la ubicación del código para trazabilidad.

### 2.1. Autenticación y gestión de sesión

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Autenticación basada en sesión** | `apps/authentication/views.py`, `apps/authentication/security.py` | Autenticación manual basada en `request.session["idUsuario"]`. No se depende exclusivamente de `request.user` de Django. |
| **Backend de autenticación personalizado** | `apps/authentication/backends.py` | `EmailBackend` autentica por email + contraseña contra el modelo `Register`. |
| **Hash de contraseñas** | `apps/authentication/security.py` | Nuevas contraseñas se hashean con **Argon2id** (`make_password` de Django). Cuentas existentes con SHA-256 siguen funcionando (verificación híbrida). |
| **Almacenamiento de contraseña en modelo** | `apps/authentication/models.py` | Campo `contrasena` (`CharField`, 255 caracteres). `set_password()` y `check_password()` delegan en `SecurityHelper`. |
| **Almacenamiento seguro de sesión** | `config/settings/base.py` | `SESSION_ENGINE = "django.contrib.sessions.backends.db"`, `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = "Lax"`. |
| **Seguridad de cookies de sesión** | `config/settings/prod.py` | `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True` en producción. |
| **Rotación de clave de sesión** | `apps/authentication/views.py` | `request.session.cycle_key()` después de login exitoso (previene session fixation). |
| **Cierre de sesión** | `apps/authentication/views.py` → `LogoutView` | `request.session.flush()` elimina toda la sesión. Requiere autenticación (`IsAuthenticated`). |

---

### 2.2. Autorización y control de acceso basado en roles (RBAC)

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Clases de permiso DRF** | `apps/core/permissions.py` | `IsAuthenticatedDRF`, `IsPaciente`, `IsProfesional`, `IsAdmin`, `IsPacienteOrProfesional`, `IsAdminOrProfesional`, `IsOwnerOrStaff`. |
| **Funciones de ayuda** | `apps/core/permissions.py` | `require_auth(request)`, `require_role(request, *roles)` para uso en servicios y vistas no-DRF. |
| **Aplicación en vistas** | Cada ViewSet de `apps/*/views.py` | Cada endpoint declara explícitamente sus `permission_classes` (ej. chatbot solo para `paciente`, panel admin solo para `admin`). |

---

### 2.3. Middleware de seguridad y cabeceras HTTP

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **SecurityMiddleware** | `django.middleware.security.SecurityMiddleware` | Encabezados de seguridad básicos de Django. |
| **SecurityHeadersMiddleware** | `apps/core/middleware/security_headers.py` | `SECURE_CONTENT_TYPE_NOSNIFF = True`, `X_FRAME_OPTIONS = "DENY"`. |
| **CSP (Content Security Policy)** | `config/settings/base.py` | `CSP_ENABLED = True`. Configurable por entorno. |
| **HSTS** | `config/settings/prod.py` | `SECURE_HSTS_SECONDS = 31536000` (solo producción). |
| **SSL Redirect** | `config/settings/prod.py` | `SECURE_SSL_REDIRECT = True` (solo producción). |
| **CSRF protección** | `django.middleware.csrf.CsrfViewMiddleware` | Protección contra Cross-Site Request Forgery en peticiones no seguras. |

---

### 2.4. Validación y sanitización de entrada

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Validación de entrada (DRF)** | `apps/authentication/serializers.py`, `apps/authentication/services.py` | Validación de email, contraseña (mínimo 6 caracteres, mayúscula, número), edad, etc. |
| **Sanitización de PII para Gemini** | `apps/chatbot/services.py` → `ChatbotService._sanitize_text()` | Enmascara emails, teléfonos, números de documento (CC, CE, TI, pasaporte) y tarjetas de crédito antes de enviar al modelo de IA. |
| **Validación de archivos subidos** | `apps/core/utils.py` → `validate_file_upload()` | Extensiones permitidas (`jpg`, `jpeg`, `png`, `pdf`, `gif`, `webp`, `doc`, `docx`), tamaño máximo (5 MB), verificación de *magic bytes*. |
| **Sanitización de texto en chatbot** | `apps/chatbot/services.py` | `_sanitize_text()` aplicado a historial y mensaje del usuario antes de enviar a Gemini. |

---

### 2.5. Rate limiting y protección contra fuerza bruta

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Rate limiting de autenticación** | `apps/authentication/repositories.py` → `SecurityRepository` | `check_brute_force()` (5 intentos → bloqueo 15 min), `register_failed_attempts()`, `reset_failed_attempts()`. |
| **Rate limiting de registro/recuperación** | `apps/authentication/repositories.py` | `check_rate_limit()` para `register:{email}` y `recovery:{email}`. |
| **Throttling de DRF** | `config/settings/base.py` | `AnonRateThrottle` (60/min), `UserRateThrottle` (120/min). |
| **Rate limiting por endpoint de autenticación** | `apps/authentication/views.py` | `LoginView` (5/min), `RegisterView` (3/min), `ForgotPasswordView` (3/min), `ResetPasswordView` (3/min), `TOTPVerifyLoginView` (5/min). |

---

### 2.6. Seguridad de sesión y cookies

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Session engine** | `config/settings/base.py` | `SESSION_ENGINE = "django.contrib.sessions.backends.db"` (almacenamiento en BD). |
| **Cookie de sesión segura** | `config/settings/base.py` | `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = "Lax"`. |
| **Cookie segura en producción** | `config/settings/prod.py` | `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`. |
| **Rotación de sesión** | `apps/authentication/views.py` | `request.session.cycle_key()` tras `django_login()`. |
| **Cierre de sesión** | `apps/authentication/views.py` → `LogoutView` | `request.session.flush()`, requiere `IsAuthenticated`. |
| **Verificación de estado de cuenta** | `apps/core/middleware/account_status.py` | Verifica `activo` y `estadoCuenta` en cada request autenticado; cierra sesión si está suspendida. |

---

### 2.7. Sanitización de datos sensibles (PII)

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Sanitización para Gemini** | `apps/chatbot/services.py` → `_sanitize_text()` | Enmascara emails, teléfonos colombianos, números de documento (CC, CE, TI, pasaporte) y tarjetas de crédito antes de enviar al modelo de IA. |
| **Aplicación en historial** | `apps/chatbot/services.py` → `_build_contents()` | Sanitiza cada mensaje del historial y el mensaje actual antes de construir el prompt. |

---

### 2.8. Almacenamiento de contraseñas

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Nuevas contraseñas** | `apps/authentication/security.py` → `SecurityHelper.hash_password()` | Usa `make_password()` de Django → **PBKDF2 con sal automática**. |
| **Verificación híbrida** | `apps/authentication/security.py` → `SecurityHelper.verify_password()` | Primero intenta Django `check_password` (PBKDF2/Argon2), si falla prueba SHA-256 puro para cuentas legacy. |
| **Detección de formato** | `SecurityHelper.is_legacy_sha256()`, `needs_upgrade()` | Detecta si el hash almacenado es SHA-256 legacy (64 hex chars) o texto plano, para decidir si migrar a Argon2id en el siguiente login. |
| **Longitud del campo** | `apps/authentication/models.py` | `contrasena = models.CharField(max_length=255)` — suficiente para hash Argon2id (~97 caracteres). |

---

### 2.9. Autenticación de dos factores (TOTP / 2FA)

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Modelo** | `apps/authentication/models.py` → `TOTPDevice` | `OneToOneField(Register)`, `secret` (base32), `confirmed`, `last_used`. |
| **Servicios** | `apps/authentication/services.py` | `create_totp_device()`, `get_totp_provisioning_uri()`, `get_totp_qr_code_svg()`, `verify_totp_token()`, `confirm_totp_device()`, `disable_totp_device()`, `is_totp_enabled()`, `require_totp_for_role()`. |
| **Vistas REST** | `apps/authentication/views.py` | `TOTPSetupView`, `TOTPConfirmView`, `TOTPDisableView`, `TOTPStatusView`, `TOTPVerifyLoginView`. |
| **Obligatoriedad por rol** | `services.py` → `require_totp_for_role(role)` | Retorna `True` para `admin` y `profesional`. |

---

### 2.10. Verificación de correo electrónico

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Modelo** | `apps/authentication/models.py` → `EmailVerificationToken` | Token único, expiración 24 horas, un solo uso (`used=True`). |
| **Campo en usuario** | `apps/authentication/models.py` → `Register.email_verificado` | `BooleanField(default=False)`. Para `profesional` es obligatorio (`False` inicialmente). |
| **Generación y envío** | `apps/authentication/services.py` → `_create_and_send_verification_email()` | Token `secrets.token_urlsafe(32)`, enlace `verify-email.html?token=...`. |
| **Endpoint de verificación** | `apps/authentication/views.py` → `VerifyEmailView` | `POST /api/verify-email/`. Valida token, marca `email_verificado=True`, invalida token. |
| **Bloqueo de login** | `apps/authentication/services.py` → `login_user()` | Si `rol == "profesional"` y `email_verificado == False`, rechaza con 403. |

---

### 2.11. Rate limiting por endpoint de autenticación

| Endpoint | Límite | Razón |
|----------|--------|-------|
| `POST /api/login` | 5 por minuto / IP | Previene fuerza bruta de contraseñas. |
| `POST /api/register` | 3 por minuto / IP | Evita creación masiva de cuentas falsas. |
| `POST /api/forgot-password` | 3 por minuto / IP | Evita enumeración de emails y spam de correos. |
| `POST /api/reset-password` | 3 por minuto / IP | Lo mismo que forgot password. |
| `POST /api/auth/totp-verify-login` | 5 por minuto / IP | Previene fuerza bruta de códigos TOTP de 6 dígitos. |

Implementado con `django-ratelimit` en `@method_decorator(ratelimit(key='ip', rate='X/m', method='POST', block=True))`.

---

### 2.12. Middleware de estado de cuenta

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Verificación en cada request** | `apps/core/middleware/account_status.py` → `AccountStatusMiddleware` | Verifica `activo` y `estadoCuenta` en cada request autenticado. Si la cuenta está suspendida, cierra sesión y devuelve 403 JSON o redirige a login. |
| **Rutas exentas** | `EXEMPT_PATHS` | `/static/`, `/healthz/`, `/api/login`, `/api/logout`, `/login.html`, `/favicon.ico`, `/api/session`, `/api/csrf`, `/legal/`, `/uploads/`. |

---

### 2.13. Validación de archivos subidos

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Validación completa** | `apps/core/utils.py` → `validate_file_upload()` | Extensión permitida, tamaño máximo (5 MB), verificación de *magic bytes* para evitar falsificación de extensión. |

---

### 2.14. Webhooks con firma HMAC (pagos Wompi)

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Verificación de firma** | `apps/billing/views.py` → `WebhookWompiView` | Valida `x-hw-signature` con `HMAC-SHA256` usando `WOMPI_INTEGRITY_SECRET` antes de procesar el pago. |

---

### 2.15. CSP y cabeceras de seguridad adicionales

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Content Security Policy** | `config/settings/base.py` → `CSP_ENABLED = True` | `apps/core/middleware/security_headers.py` inyecta cabeceras CSP. En desarrollo: `Content-Security-Policy-Report-Only`. En producción: `Content-Security-Policy` enforce. |
| **Content-Type: nosniff** | `config/settings/base.py` | `SECURE_CONTENT_TYPE_NOSNIFF = True`. |
| **X-Frame-Options** | `config/settings/base.py` | `X_FRAME_OPTIONS = "DENY"`. |
| **HSTS** | `config/settings/prod.py` | `SECURE_HSTS_SECONDS = 31536000` (solo producción). |
| **SSL Redirect** | `config/settings/prod.py` | `SECURE_SSL_REDIRECT = True` (solo producción). |

---

## Flujo de login y migración de contraseñas

El sistema soporta tres formatos de contraseña en la columna `contrasena` de la tabla `Register`:

1. **SHA-256 puro** (64 caracteres hexadecimales): cuentas creadas anteriormente con `SecurityHelper` anterior.
2. **PBKDF2 de Django** (formato `pbkdf2_sha256$...`): cuentas creadas por el panel de administración o migraciones anteriores.
3. **Argon2id** (formato `argon2$...`): cuentas nuevas creadas mediante registro o restablecimiento de contraseña.

### Flujo de inicio de sesión

1. El usuario envía email y contraseña en texto plano.
2. `build_response` / `login_user` obtiene el hash almacenado en la columna `contrasena`.
3. `SecurityHelper.verify_password(password, stored_hash)`:
   - Si el hash es SHA-256 de 64 caracteres → compara con `hashlib.sha256(password).hexdigest()`.
   - Si el hash es texto plano (usuario creado directamente en MySQL sin hash) → compara directamente y **marca para rehash**.
   - Si es PBKDF2, Argon2id u otro hash de Django → usa `django_check(password, hashed)`.
4. Si el hash no es Argon2id (es decir, es SHA-256 legacy o texto plano), `needs_upgrade()` retorna `True` y se ejecuta `repo.update_password(usuario_id, SecurityHelper.hash_password(password))`, migrando la cuenta al nuevo algoritmo sin intervención del usuario.

Así, las cuentas existentes con SHA-256 siguen funcionando sin intervención del usuario, y al iniciar sesión se actualizan silenciosamente a Argon2id.

---

## Recomendaciones prioritarias (pendientes)

1. **Arreglar hash de contraseñas** → usar `make_password` de Django (PBKDF2) en lugar de SHA-256 simple para cuentas nuevas (`apps/authentication/security.py`).
2. **Remover `DEMO_PAGO = true`** del código de producción (`templates/patient/aside-patient/facturas.html`).
3. **Revisar templates** que usan `request.user` → usar datos de sesión o context processor adecuado (`templates/patient/patient.dashboard.html`, `templates/professional/profesional.dashboard.html`).
4. **Revisar hash de contraseñas** → migrar de SHA-256 a PBKDF2 (`apps/authentication/security.py`).

---

## Cosas que NO son bugs (verificadas)

- `AccountStatusMiddleware` está correctamente configurado en `MIDDLEWARE` de `settings/base.py`.
- `IsAuthenticatedDRF` establece `request.user_id`, `request.user_role`, `request.user_name` correctamente para las vistas que lo usan.
- `ChatMensajeViewSet` en chatbot usa `request.user_id` correctamente (establecido por `IsAuthenticatedDRF`).
- `ProfessionalPaymentInfoViewSet.update` funciona correctamente (aunque ligeramente ineficiente).
- `Facturas.to_dict()` accede correctamente a `self.items.all()` (related_name válido).
- `recover_password` invalida tokens previos correctamente.

---

## Checklist de despliegue a producción

- [ ] `pip install -r requirements.txt` (incluye `argon2-cffi>=23.1.0`).
- [ ] `python manage.py migrate` (aplica migración `0004_migrate_contrasena_to_argon2.py`).
- [ ] Variables de entorno: `SECRET_KEY` fuerte, `DEBUG=False`, `ALLOWED_HOSTS`, `CORS_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `EMAIL_*`, `WOMPI_*`, `GEMINI_API_KEY*`, `SITE_URL`.
- [ ] `CSP_ENABLED=True` → cabecera CSP enforce en producción.
- [ ] `CSRF_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SECURE=True` (ya en `prod.py`).
- [ ] `SESSION_COOKIE_SECURE=True`.
- [ ] HSTS activado (`SECURE_HSTS_SECONDS=31536000` en `prod.py`).
- [ ] Certificados TLS válidos (Let's Encrypt o proveedor).
- [ ] Probar flujo completo: registro → verificación email → login → 2FA setup → login con 2FA.
- [ ] Verificar cabeceras con `curl -I https://dominio.com` → CSP, HSTS, X-Frame-Options, etc.
- [ ] Escaneo de vulnerabilidades (OWASP ZAP, Snyk, etc.) post-despliegue.
- [ ] Verificar que `ALLOW_PLAINTEXT_BOOTSTRAP=False` en producción.

---

*Documento generado automáticamente como parte de la documentación de seguridad de PsyAI Connect. Mantener actualizado ante cualquier cambio en la arquitectura de autenticación y autorización.*
