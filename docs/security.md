# Documentación de Seguridad — PsyAI Connect

> **Versión:** 1.2  
> **Estado:** Documento activo. Refleja el estado real del código fuente en `config/settings/`, `apps/authentication/`, `apps/core/` y `apps/chatbot/`.  
> **Audiencia:** desarrolladores, auditores de seguridad y equipo de operaciones.  
> **Enfoque:** defensa en capas (defense in depth) — autenticación, autorización, transporte, entrada, almacenamiento y auditoría.

---

## 1. Modelo de amenazas y principios

| Principio | Descripción |
|-----------|-------------|
| **Defensa en capas** | Ninguna medida de seguridad es suficiente por sí sola; se aplican controles en transporte, autenticación, autorización, entrada y salida. |
| **Autenticación basada en sesión** | El sistema usa `request.session` (no exclusivamente `request.user` de Django) para identificar al usuario autenticado. |
| **Autorización por rol (RBAC)** | Tres roles (`paciente`, `profesional`, `admin`) con clases DRF explícitas por endpoint. |
| **Cero confianza en datos de entrada** | Toda entrada del usuario se valida y sanita antes de procesarla o enviarla a modelos de IA. |
| **Contraseñas nunca en texto plano** | Hash con Argon2id (Django default); verificación híbrida para SHA-256 legacy; opción de texto plano solo para bootstrap (`ALLOW_PLAINTEXT_BOOTSTRAP=False` por defecto). |
| **Auditoría de acciones** | Middleware de auditoría registra acciones sensibles con máscara de PII (emails, IPs truncadas). |

---

## 2. Arquitectura de seguridad por capas

### Capa 1 — Transporte (TLS / HTTPS)

| Componente | Archivo | Configuración | Entorno |
|------------|---------|---------------|---------|
| SSL Redirect | `config/settings/prod.py` | `SECURE_SSL_REDIRECT = True` | Producción |
| Proxy SSL header | `config/settings/prod.py` | `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` | Detrás de load balancer |
| HSTS | `config/settings/prod.py` | `SECURE_HSTS_SECONDS = 31536000`, `INCLUDE_SUBDOMAINS = True`, `PRELOAD = True` | Producción |
| Cookie segura (sesión) | `config/settings/prod.py` | `SESSION_COOKIE_SECURE = True` | Producción |
| Cookie segura (CSRF) | `config/settings/prod.py` | `CSRF_COOKIE_SECURE = True` | Producción |
| Cookie HttpOnly | `config/settings/base.py` | `SESSION_COOKIE_HTTPONLY = True`, `CSRF_COOKIE_HTTPONLY = True` | Todos |
| Cookie SameSite | `config/settings/base.py` | `SESSION_COOKIE_SAMESITE = "Lax"`, `CSRF_COOKIE_SAMESITE = "Lax"` | Todos |

---

### Capa 2 — Autenticación

#### 2.1. Modelo de usuario (`Register`)

Archivo: `apps/authentication/models.py`

`Register` extiende `AbstractBaseUser` con `USERNAME_FIELD = "email"`. El usuario se autentica por email, no por nombre de usuario.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `idUsuario` | AutoField (PK) | Identificador único |
| `nombre` | CharField(120) | Nombre completo |
| `email` | EmailField (único) | Credencial de login |
| `password` | CharField(255, db_column=`contrasena`) | Hash bcrypt / Argon2id / SHA-256 legacy |
| `rol` | CharField(20) | `choices=[paciente, profesional, admin]` |
| `fotoPerfil` | CharField(255) | URL de foto de perfil |
| `estadoCuenta` | CharField(20) | `choices=[Activa, Suspendida]`, default `Activa` |
| `activo` | BooleanField | default `True` |
| `email_verificado` | BooleanField | default `False` |
| `fechaRegistro` | DateTimeField | auto_now_add |

Propiedades derivadas:
- `is_staff` / `is_superuser`: `True` solo si `rol == "admin"`.
- `set_password()` / `check_password()`: delegan en `SecurityHelper` (`apps/authentication/security.py`).

#### 2.2. Backend de autenticación (`EmailBackend`)

Archivo: `apps/authentication/backends.py`

Autentica por email + contraseña contra `Register`. Usa `SecurityHelper.verify_password()` para soportar múltiples formatos de hash.

#### 2.3. Sesión y rotación de clave

- **Motor de sesión:** `django.contrib.sessions.backends.db` (almacenamiento en BD, `config/settings/base.py`).
- **Vida de sesión:** `SESSION_COOKIE_AGE = 604800` (7 días).
- **Rotación tras login:** `request.session.cycle_key()` en `apps/authentication/views.py` (previene session fixation).
- **Cierre de sesión:** `request.session.flush()` en `LogoutView` (requiere `IsAuthenticated`).
- **Verificación por request:** `AccountStatusMiddleware` valida `activo` y `estadoCuenta='Activa'` en cada petición autenticada. Si la cuenta está suspendida, limpia la sesión y devuelve 403 JSON o redirige a `/login.html?suspendida=1`.

Rutas exentas de verificación de estado de cuenta: `/static/`, `/healthz/`, `/api/login`, `/api/logout`, `/login.html`, `/favicon.ico`, `/api/session`, `/api/csrf`, `/legal/`, `/uploads/`.

#### 2.4. Formatos de contraseña soportados (verificación híbrida)

Archivo: `apps/authentication/security.py` → `SecurityHelper`

El sistema soporta tres formatos en la columna `contrasena`:

| Formato | Patrón | Método de verificación | Migración |
|---------|--------|------------------------|-----------|
| **SHA-256 legacy** | 64 caracteres hexadecimales | `hashlib.sha256(password).hexdigest()` comparado con `hmac.compare_digest` | No se toca (funciona tal cual) |
| **Django hash (PBKDF2 / Argon2id)** | `pbkdf2_sha256$...` o `argon2$...` | `django.contrib.auth.hashers.check_password()` | No se toca |
| **Texto plano** | Cualquier texto no hash | Comparación directa solo si `ALLOW_PLAINTEXT_BOOTSTRAP=True` | Se marca para rehash al siguiente login |

`SecurityHelper.hash_password()` usa `make_password()` de Django → Argon2id por defecto (configurado en `PASSWORD_HASHERS` de `config/settings/base.py`):
```
Argon2PasswordHasher → PBKDF2PasswordHasher → BCryptSHA256PasswordHasher
```

`needs_upgrade()` retorna `True` solo para texto plano (bootstrap). Los hashes SHA-256 existentes **no se migran automáticamente** — siguen funcionando sin intervención del usuario.

#### 2.5. Validadores de contraseña (`AUTH_PASSWORD_VALIDATORS`)

Archivo: `config/settings/base.py`

| Validador | Propósito |
|-----------|-----------|
| `UserAttributeSimilarityValidator` | Rechaza contraseñas similares a atributos del usuario |
| `MinimumLengthValidator` | Mínimo 10 caracteres |
| `CommonPasswordValidator` | Rechaza contraseñas comunes |
| `NumericPasswordValidator` | Rechaza contraseñas solo numéricas |

#### 2.6. Verificación de dos factores (TOTP / 2FA)

Archivo: `apps/authentication/models.py` → `TOTPDevice`  
Archivo: `apps/authentication/services.py` → `AuthService`  
Archivo: `apps/authentication/views.py` → vistas REST

| Componente | Descripción |
|------------|-------------|
| Modelo `TOTPDevice` | `OneToOneField(Register)`, `secret` (base32), `confirmed`, `last_used`, `createdAt`. Tabla `TOTPDevices`. |
| RFC 6238 / RFC 4226 | Compatible con Google Authenticator, Authy, etc. |
| Servicios | `create_totp_device()`, `get_totp_provisioning_uri()`, `get_totp_qr_code_svg()`, `verify_totp_token()`, `confirm_totp_device()`, `disable_totp_device()`, `is_totp_enabled()`, `require_totp_for_role()`. |
| Vistas REST | `TOTPSetupView`, `TOTPConfirmView`, `TOTPDisableView`, `TOTPStatusView`, `TOTPVerifyLoginView`. |
| Obligatoriedad por rol | `require_totp_for_role(role)` retorna `True` para `admin` y `profesional`; `False` para `paciente`. |
| Rate limiting TOTP login | `TOTPVerifyLoginView` limitado a 5/min por IP (`django-ratelimit`). |

#### 2.7. Verificación de correo electrónico

Archivo: `apps/authentication/models.py` → `EmailVerificationToken`  
Archivo: `apps/authentication/services.py`  
Archivo: `apps/authentication/views.py` → `VerifyEmailView`

| Componente | Descripción |
|------------|-------------|
| Modelo | Token único, expiración 24 horas, un solo uso (`used=True`). Tabla `EmailVerificationTokens`. |
| Campo en usuario | `Register.email_verificado` (`BooleanField(default=False)`). Obligatorio para rol `profesional`. |
| Generación | `secrets.token_urlsafe(32)`, enlace `verify-email.html?token=...`. |
| Endpoint | `POST /api/verify-email/` valida token, marca `email_verificado=True`, invalida el token. |
| Bloqueo de login | Si `rol == "profesional"` y `email_verificado == False`, `login_user()` rechaza con 403. |
| Recuperación de contraseña | `RecoveryTokens` (tabla `RecoveryTokens`) con token, expiración y un solo uso. Endpoints: `POST /api/forgot-password`, `POST /api/reset-password`. |

---

### Capa 3 — Autorización (RBAC)

Archivo principal: `apps/core/permissions.py`  
Utilidades: `apps/core/utils.py` → `AuthHelper`

#### 3.1. Clases de permiso DRF

| Clase | Lógica | Uso típico |
|-------|--------|------------|
| `IsAuthenticatedDRF` | Intenta `request.user` (DRF/token); fallback a sesión. Valida `activo` y `estadoCuenta='Activa'` en BD. Setea `request.user_id`, `request.user_role`, `request.user_name`. | Base para todos los endpoints privados |
| `IsPaciente` | `request.user_role == 'paciente'` | Endpoints solo pacientes |
| `IsProfesional` | `request.user_role == 'profesional'` | Endpoints solo profesionales |
| `IsAdmin` | `request.user_role == 'admin'` | Panel de administración |
| `IsPacienteOrProfesional` | `rol IN ('paciente','profesional')` | Endpoints compartidos |
| `IsAdminOrProfesional` | `rol IN ('admin','profesional')` | Reportes, métricas, disponibilidad |
| `IsOwnerOrStaff` | Dueño del objeto O admin/profesional | Objetos propios (documentos, evolución) |

#### 3.2. Flujo interno de autenticación DRF

1. Intenta `request.user.is_authenticated` (autenticación DRF/token).
2. Si existe, busca `Register` por `idUsuario`/`pk`, valida `activo` y `estadoCuenta`, setea atributos en `request`.
3. Si no hay usuario DRF, fallback a sesión: `AuthHelper.get_current_user(request)` lee `idUsuario`, `rol`, `nombre` de `request.session`.
4. Busca el `Register` en BD por `idUsuario`.
5. Rechaza si `activo=False` o `estadoCuenta != 'Activa'` (limpia sesión con `flush()`).
6. Setea `request.user_id`, `request.user_role` (minúsculas), `request.user_name`.

#### 3.3. Utilidades para vistas no-DRF

| Función | Descripción |
|---------|-------------|
| `AuthHelper.require_auth(request)` | Valida sesión y estado de cuenta. Retorna 401/403 si falla. |
| `AuthHelper.require_role(request, *roles)` | Igual que `require_auth` más verificación de rol. Retorna 403 si no coincide. |

---

### Capa 4 — Rate limiting y protección contra fuerza bruta

Archivo: `apps/authentication/repositories.py` → `SecurityRepository`  
Archivo: `config/settings/base.py` → `REST_FRAMEWORK` throttling  
Archivo: `apps/authentication/views.py` → decoradores `django-ratelimit`

#### 4.1. Throttling de DRF (API global)

| Clase | Límite | Alcance |
|-------|--------|---------|
| `AnonRateThrottle` | 60/min | Usuarios no autenticados |
| `UserRateThrottle` | 120/min | Usuarios autenticados |

Configurado en `REST_FRAMEWORK.DEFAULT_THROTTLE_CLASSES` y `DEFAULT_THROTTLE_RATES` de `config/settings/base.py`.

#### 4.2. Rate limiting por endpoint de autenticación

| Endpoint | Límite | Razón |
|----------|--------|-------|
| `POST /api/login` | 5/min por IP | Fuerza bruta de contraseñas |
| `POST /api/register` | 3/min por IP | Cuentas falsas masivas |
| `POST /api/forgot-password` | 3/min por IP | Enumeración de emails y spam |
| `POST /api/reset-password` | 3/min por IP | Lo mismo que forgot-password |
| `POST /api/auth/totp-verify-login` | 5/min por IP | Fuerza bruta de códigos TOTP de 6 dígitos |

Implementado con `@method_decorator(ratelimit(key='ip', rate='X/m', method='POST', block=True))`.

#### 4.3. Bloqueo por intentos fallidos (`IntentosFallidos`)

Archivo: `apps/authentication/models.py` → `IntentosFallidos`  
Archivo: `apps/authentication/repositories.py` → `SecurityRepository`

| Comportamiento | Umbral | Acción |
|----------------|--------|--------|
| Registro de intento fallido | — | Incrementa contador por email |
| Bloqueo tras 5 intentos | `intentos >= 5` | `bloqueado_hasta = ahora + 15 min` |
| `check_brute_force(email)` | — | Retorna si está bloqueado y segundos restantes |
| `reset_failed_attempts(email)` | — | Reinicia contador y bloqueo tras login exitoso |
| `check_rate_limit(key, ...)` | configurable | Bloqueo temporal por clave (registro, recuperación) |

---

### Capa 5 — Validación y sanitización de entrada

#### 5.1. Validación de archivos subidos

Archivo: `apps/core/utils.py` → `FileValidator.validate()` / `validate_file_upload()`

| Control | Valor | Descripción |
|---------|-------|-------------|
| Extensiones permitidas | `jpg,jpeg,png,pdf,gif,webp,doc,docx` | Desde `ALLOWED_UPLOAD_EXTENSIONS` (env) |
| Tamaño máximo | 5 MB | Desde `MAX_UPLOAD_SIZE_MB` (env) |
| Magic bytes | Verificación | Comprueba que el contenido coincida con la extensión (evita falsificación) |
| Detección DOCX | `zipfile.ZipFile` | Para `.doc`/`.docx` verifica estructura ZIP interna |

#### 5.2. Sanitización de PII para Gemini (chatbot)

Archivo: `apps/chatbot/services.py` → `ChatbotService._sanitize_text()`

Antes de enviar cualquier mensaje al modelo de Gemini, se enmascara:
- Correos electrónicos
- Teléfonos colombianos
- Números de documento (CC, CE, TI, pasaporte)
- Tarjetas de crédito

Se aplica al historial de conversación y al mensaje actual antes de construir el prompt (`_build_contents()`).

#### 5.3. Validación DRF (serializers)

Archivo: `apps/authentication/serializers.py`

Validación de email, contraseña (mínimo 6 caracteres, mayúscula, número), edad, etc. en endpoints de registro, login, recuperación y restablecimiento.

---

### Capa 6 — Middleware de seguridad y cabeceras HTTP

Archivo: `apps/core/middleware/security_headers.py` → `SecurityHeadersMiddleware`  
Archivo: `config/settings/base.py` y `prod.py`

#### 6.1. Cabeceras inyectadas por `SecurityHeadersMiddleware`

| Cabecera | Valor | Propósito |
|----------|-------|-----------|
| `X-Content-Type-Options` | `nosniff` | Evita MIME-sniffing del navegador |
| `X-XSS-Protection` | `1; mode=block` | Filtro XSS reflejado (legacy, defensa en profundidad) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limita información del referer |
| `Content-Security-Policy` | Ver abajo | Controla fuentes de recursos (en prod se enforced; en dev es `Report-Only`) |
| `frame-ancestors` | `'none'` | Evita clickjacking (complementa `X-Frame-Options`) |
| `base-uri` | `'self'` | Evita inyección de `<base>` malicioso |
| `form-action` | `'self'` | Restringe a dónde pueden enviar formularios |

#### 6.2. Content Security Policy (CSP)

Configuración en `SecurityHeadersMiddleware` cuando `CSP_ENABLED=True`:

```
default-src 'self';
script-src 'self' 'unsafe-inline' https://accounts.google.com https://apis.google.com https://cdn.jsdelivr.net;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net;
font-src 'self' data: https://fonts.gstatic.com;
img-src 'self' data: https:;
connect-src 'self' https://accounts.google.com https://oauth2.googleapis.com;
frame-src 'self' https://accounts.google.com;
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
```

- **Desarrollo (`DEBUG=True`):** `Content-Security-Policy-Report-Only` (no rompe funcionalidad mientras se ajusta).
- **Producción:** `Content-Security-Policy` (enforced).

#### 6.3. Cabeceras de Django (`SecurityMiddleware` + `XFrameOptionsMiddleware`)

| Configuración | Archivo | Valor (producción) |
|---------------|---------|-------------------|
| `SECURE_CONTENT_TYPE_NOSNIFF` | `base.py` / `prod.py` | `True` |
| `X_FRAME_OPTIONS` | `base.py` / `prod.py` | `"DENY"` |
| `SECURE_HSTS_SECONDS` | `prod.py` | `31536000` (1 año) |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `prod.py` | `True` |
| `SECURE_HSTS_PRELOAD` | `prod.py` | `True` |
| `SECURE_SSL_REDIRECT` | `prod.py` | `True` |
| `SECURE_PROXY_SSL_HEADER` | `prod.py` | `("HTTP_X_FORWARDED_PROTO", "https")` |

---

### Capa 7 — Almacenamiento de datos sensibles

#### 7.1. Contraseñas

Ver sección **2.4** (formatos híbridos) y `PASSWORD_HASHERS` en `config/settings/base.py`:
```
Argon2PasswordHasher → PBKDF2PasswordHasher → BCryptSHA256PasswordHasher
```

Campo `contrasena` (`CharField(max_length=255)`) suficiente para hash Argon2id (~97 caracteres).

#### 7.2. Tokens de recuperación y verificación email

| Modelo | Tabla | Un solo uso | Expiración |
|--------|-------|-------------|------------|
| `RecoveryTokens` | `RecoveryTokens` | Sí (`used=True`) | 24 horas |
| `EmailVerificationToken` | `EmailVerificationTokens` | Sí (`used=True`) | 24 horas |

Ambos invalidan tokens previos no usados al crear uno nuevo (evita acumulación de tokens válidos).

#### 7.3. Consentimientos (Ley 1581/2012 Colombia)

Archivo: `apps/authentication/models.py` → `ConsentimientoUsuario`

| Campo | Descripción |
|-------|-------------|
| `tipo` | `terminos_privacidad`, `datos_sensibles_ia`, `whatsapp` |
| `version` | `LEGAL_VERSION` (env, default `2026-10-26`) |
| `aceptado` | Boolean |
| `fecha` | Timestamp de aceptación |
| `ip` / `userAgent` | Metadatos de aceptación |

`unique_together = (idUsuario, tipo, version)` — evita duplicados.

---

### Capa 8 — Webhooks con firma HMAC (pagos Wompi)

Archivo: `apps/billing/views.py` → `WebhookWompiView`

| Componente | Descripción |
|------------|-------------|
| Firma | `x-hw-signature` validada con `HMAC-SHA256` usando `WOMPI_INTEGRITY_SECRET` |
| Propósito | Garantiza que el webhook proviene realmente de Wompi y no ha sido alterado |
| Fuente de verdad | El webhook es la fuente autoritativa de estado de pago (no la confirmación frontend) |

---

### Capa 9 — Auditoría de actividad

Archivo: `apps/core/middleware/audit.py` → `AuditActivityMiddleware`

| Control | Descripción |
|---------|-------------|
| Registro de acciones | Cada petición mutante (POST/PUT/PATCH/DELETE) se clasifica y registra |
| Máscara de PII | Emails enmascarados (`_mask_email`: `f***@dominio.com`), IPs truncadas a 50 caracteres |
| Rutas excluidas | Endpoints de administración, logs, stats, CSRF, sesión, tema, newsletter, WhatsApp, chatbot (no se auditan mensajes del chatbot por privacidad) |
| Actor | Extraído de `request.session` (`idUsuario`, `nombre`, `rol`) |

---

## 3. Matriz de controles por área

| Área | Controles principales | Archivos clave |
|------|----------------------|----------------|
| Autenticación | Email backend, sesión, ciclo de clave, bcrypt/Argon2id | `backends.py`, `security.py`, `views.py` |
| Autorización | 7 clases DRF RBAC, `IsOwnerOrStaff` | `apps/core/permissions.py` |
| Sesión | DB engine, HttpOnly, SameSite, Secure (prod), rotación | `base.py`, `prod.py`, `views.py` |
| Fuerza bruta | Rate limiting por endpoint, bloqueo 15 min tras 5 fallos | `repositories.py`, `views.py` |
| Entrada | Validación archivos (ext, tamaño, magic bytes), DRF serializers | `apps/core/utils.py`, `serializers.py` |
| PII / IA | Sanitización antes de Gemini (emails, teléfonos, documentos, tarjetas) | `apps/chatbot/services.py` |
| Cabeceras HTTP | CSP, HSTS, X-Frame-Options, nosniff, Referrer-Policy | `security_headers.py`, `base.py`, `prod.py` |
| Webhooks | HMAC-SHA256 con `WOMPI_INTEGRITY_SECRET` | `apps/billing/views.py` |
| 2FA | TOTP RFC 6238, obligatorio para admin/profesional | `TOTPDevice`, `AuthService`, vistas REST |
| Email verificado | Token un uso, 24h, bloqueo profesional si no verificado | `EmailVerificationToken`, `VerifyEmailView` |
| Estado de cuenta | Middleware verifica activo/estadoCuenta en cada request | `account_status.py` |
| Auditoría | Registro de acciones con máscara de PII | `audit.py` |
| Consentimiento | Ley 1581/2012, versionado de textos legales | `ConsentimientoUsuario` |

---

## 4. Flujo de login completo

```
1. Usuario envía email + contraseña → POST /api/login
   ├── Rate limit: 5/min por IP (django-ratelimit)
   │
2. EmailBackend.authenticate(email, password)
   ├── SecurityHelper.verify_password() → SHA-256 / Django hash / texto plano
   │
3. Si credenciales válidas:
   ├── Verificar estadoCuenta == 'Activa' y activo == True
   ├── Si rol == profesional: verificar email_verificado == True (si no → 403)
   ├── Si 2FA requerido para el rol: crear sesión temporal pending_2fa
   │   └── Usuario debe completar TOTPVerifyLoginView (5/min por IP)
   │
4. Login exitoso:
   ├── request.session.cycle_key() (anti session fixation)
   ├── register_login_event() → tabla Login (auditoría de accesos)
   ├── reset_failed_attempts(email) → limpia IntentosFallidos
   │
5. Si credenciales inválidas:
   ├── register_failed_attempt(email) → incrementa IntentosFallidos
   ├── Si intentos >= 5 → bloqueado_hasta = ahora + 15 min
   └── Respuesta 401 (sin revelar si el email existe)
```

---

## 5. Checklist de despliegue a producción

- [ ] `SECRET_KEY` fuerte (>50 caracteres, no el valor por defecto `dev-insecure-key-change-me`). `prod.py` sale con error si es insegura.
- [ ] `DEBUG = False` en `config/settings/prod.py`.
- [ ] `ALLOWED_HOSTS` y `CORS_ORIGINS` con dominios reales (no `*` en producción).
- [ ] `CSRF_TRUSTED_ORIGINS` coincide con `CORS_ORIGINS`.
- [ ] `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True` (ya en `prod.py`).
- [ ] `SECURE_SSL_REDIRECT = True` y `SECURE_PROXY_SSL_HEADER` si hay load balancer.
- [ ] `SECURE_HSTS_SECONDS = 31536000`, `INCLUDE_SUBDOMAINS = True`, `PRELOAD = True`.
- [ ] `CSP_ENABLED = True` → cabecera CSP enforced en producción.
- [ ] Certificados TLS válidos (Let's Encrypt o proveedor).
- [ ] `ALLOW_PLAINTEXT_BOOTSTRAP = False` (default, nunca habilitar en producción).
- [ ] Variables de entorno: `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `WOMPI_INTEGRITY_SECRET`, `GEMINI_API_KEY*`, `SITE_URL`, `TWILIO_*`.
- [ ] `pip install -r requirements.txt` (incluye `argon2-cffi` para Argon2id).
- [ ] `python manage.py migrate` (aplica todas las migraciones de seguridad).
- [ ] Probar flujo completo: registro → verificación email → login → 2FA (si aplica) → acceso restringido por rol.
- [ ] Verificar cabeceras con `curl -I https://dominio.com`: CSP, HSTS, X-Frame-Options, X-Content-Type-Options.
- [ ] Escaneo de vulnerabilidades (OWASP ZAP, Snyk, etc.) post-despliegue.

---

## 6. Archivos clave de seguridad

| Ruta | Contenido |
|------|-----------|
| `apps/authentication/security.py` | `SecurityHelper`: hash (Argon2id), verificación híbrida SHA-256/Django/texto plano, `needs_upgrade()` |
| `apps/authentication/backends.py` | `EmailBackend`: autenticación por email |
| `apps/authentication/models.py` | `Register`, `Login`, `RecoveryTokens`, `EmailVerificationToken`, `IntentosFallidos`, `TOTPDevice`, `ConsentimientoUsuario` |
| `apps/authentication/repositories.py` | `AuthRepository`, `SecurityRepository`: brute force, rate limiting, TOTP, tokens |
| `apps/authentication/views.py` | Vistas de login, registro, recuperación, 2FA, logout, rate limiting por endpoint |
| `apps/authentication/services.py` | `AuthService`: login, TOTP, email verificación, recuperación de contraseña |
| `apps/authentication/serializers.py` | Validación de entrada de endpoints de autenticación |
| `apps/core/permissions.py` | 7 clases de permiso DRF RBAC, `require_auth`, `require_role` |
| `apps/core/utils.py` | `AuthHelper`, `FileValidator` (extensión, tamaño, magic bytes) |
| `apps/core/middleware/security_headers.py` | `SecurityHeadersMiddleware`: CSP, X-Content-Type-Options, Referrer-Policy, etc. |
| `apps/core/middleware/account_status.py` | `AccountStatusMiddleware`: verifica activo/estadoCuenta en cada request |
| `apps/core/middleware/audit.py` | `AuditActivityMiddleware`: registro de acciones con máscara de PII |
| `apps/chatbot/services.py` | `_sanitize_text()`: enmascara PII antes de enviar a Gemini |
| `apps/billing/views.py` | `WebhookWompiView`: verificación HMAC-SHA256 |
| `config/settings/base.py` | `PASSWORD_HASHERS`, `AUTH_PASSWORD_VALIDATORS`, `REST_FRAMEWORK` throttling, cookies, CSP, upload limits |
| `config/settings/prod.py` | `SECRET_KEY` validación, cookies seguras, HSTS, SSL redirect, proxy SSL header |
| `config/settings/dev.py` | `DEBUG=True`, `ALLOWED_HOSTS=["*"]`, `CORS_ALLOW_ALL_ORIGINS=True`, email por consola |

---

## 7. Ver también

- [`roles-and-permissions.md`](roles-and-permissions.md) — Modelo de roles y clases de permiso DRF
- [`deployment.md`](deployment.md) — Variables de entorno y despliegue con Docker
- [`chatbot-ai.md`](chatbot-ai.md) — Sanitización de PII para Gemini, detección de riesgo
- [`data-models.md`](data-models.md) — Modelos de autenticación y seguridad
- [`api.md`](api.md) — Referencia completa de endpoints con permisos requeridos
- [`architecture.md`](architecture.md) — Arquitectura general del sistema
