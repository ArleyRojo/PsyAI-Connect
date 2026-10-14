# SEGURIDAD.md — Estado de Seguridad de PsyAI Connect

> **Versión:** 1.0  
> **Fecha:** 2026-09-21  
> **Alcance:** Documenta las capas de seguridad implementadas en PsyAI Connect, tanto las preexistentes como las agregadas en esta iteración.  
> **Audiencia:** Equipo de desarrollo, dueño de producto, auditoría.

---

## 1. Capas de seguridad implementadas (estado base)

A continuación se describen los controles de seguridad que **ya existían** en el proyecto antes de esta iteración. Cada uno incluye la ubicación del código para trazabilidad.

| # | Control | Descripción breve | Ubicación |
|---|---------|-------------------|-----------|
| 1 | **Autenticación por sesión (Django)** | Login basado en `request.session` con backend personalizado (`EmailBackend`). Las contraseñas se almacenan con hash (bcrypt/SHA-256 — *fuera de alcance de este documento*). | `apps/authentication/backends.py`, `apps/authentication/security.py` |
| 2 | **Protección contra fuerza bruta** | Límite de 5 intentos fallidos → bloqueo 15 min. Aplicado a login, registro y recuperación de contraseña. | `apps/authentication/repositories.py` → `SecurityRepository.check_brute_force`, `register_failed_attempt`, `check_rate_limit` |
| 3 | **Autorización por roles (RBAC)** | Permisos DRF: `IsAuthenticatedDRF`, `IsPaciente`, `IsProfesional`, `IsAdmin`, `IsPacienteOrProfesional`, `IsAdminOrProfesional`, `IsOwnerOrStaff`. | `apps/core/permissions.py` |
| 4 | **Cabeceras de seguridad HTTP** | Middleware que añade `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`. HSTS, cookies `Secure`/`HttpOnly` en `prod.py`. | `apps/core/middleware/security_headers.py`, `config/settings/prod.py` |
| 5 | **Verificación HMAC en webhook Wompi** | Validación de firma `X-Event-Checksum` con `hmac.compare_digest` antes de procesar pagos. | `apps/billing/views.py` → `WebhookWompiView` |
| 6 | **Validación de archivos subidos** | Extensión permitida, tamaño máx. (5 MB), y verificación de *magic bytes* (JPEG, PNG, PDF, etc.). | `apps/core/utils.py` → `validate_file_upload` |
| 7 | **Throttling DRF** | `AnonRateThrottle` (60/min) y `UserRateThrottle` (120/min) configurados globalmente. | `config/settings/base.py` → `REST_FRAMEWORK.DEFAULT_THROTTLE_*` |
| 8 | **CORS restringido** | `CORS_ALLOW_CREDENTIALS = True` + lista explícita `CORS_ORIGINS` / `CSRF_TRUSTED_ORIGINS`. | `config/settings/base.py` |
| 9 | **Tokens de recuperación de contraseña** | Token `secrets.token_urlsafe(32)`, expiración 1 hora, un solo uso (`used=True` tras consumir). | `apps/authentication/services.py` → `recover_password`, `reset_password` |
| 10 | **Validación de `SECRET_KEY` fuerte** | Arranque falla en `prod.py` si `SECRET_KEY` ausente, < 50 chars, o usa valor dev. | `config/settings/prod.py` (líneas 16-23) |

---

## 2. Capas de seguridad agregadas en esta iteración

A continuación se detallan los **6 controles nuevos** implementados para cubrir los hallazgos de seguridad identificados. Cada uno explica **qué se cambió**, **por qué**, y **dónde vive el código**.

---

### 2.1 CSRF real en toda la API DRF (hallazgo #1)

**Problema:**  
El login manual (`request.session["idUsuario"] = …` sin `django.contrib.auth.login()`) dejaba `request.user = AnonymousUser`. DRF solo ejecuta `SessionAuthentication.enforce_csrf()` si `authenticate()` devuelve usuario válido → **todos los endpoints `/api/…` aceptaban `POST/PUT/DELETE` sin token CSRF**.

**Solución implementada:**

| Componente | Qué hace |
|------------|----------|
| `CsrfEnforcedSessionAuthentication` (`apps/authentication/authentication.py`) | Subclase de `SessionAuthentication` que **fuerza** `enforce_csrf()` cuando hay sesión activa (`request.session["idUsuario"]`), independientemente de `request.user`. |
| `CsrfExemptSessionAuthentication` | Variante sin CSRF para endpoints públicos (login, registro, recuperación). |
| `DEFAULT_AUTHENTICATION_CLASSES` → `CsrfEnforcedSessionAuthentication` | Ahora es el default en `config/settings/base.py`. |
| Endpoint `GET /api/csrf/` (`CsrfTokenView`) | Expone el token CSRF para que el frontend lo lea y envíe en header `X-CSRFToken`. |
| `csrf.js` (`static/js/core/shared/csrf.js`) | Helper centralizado: `fetchWithCsrf()` inyecta `X-CSRFToken` automáticamente en `POST/PUT/PATCH/DELETE`. Lee el token de cookie, meta-tag `<meta name="csrf-token">`, o variable global `window.CSRF_TOKEN`. |
| `CSRF_COOKIE_HTTPONLY = False` en `dev.py` | En desarrollo permite leer la cookie desde JS. En producción (`prod.py`) queda `True`; el frontend usa el endpoint `/api/csrf/` o el meta-tag. |
| `django.contrib.auth.login()` + `request.session.cycle_key()` en `LoginView` | Integra el login real con Django → `request.user` poblado → DRF puede aplicar CSRF nativo. Rotación de sesión previene *session fixation*. |

**Archivos tocados:**
- `apps/authentication/authentication.py` (nuevo)
- `apps/authentication/views.py` → `LoginView`, `CsrfTokenView`
- `apps/authentication/urls.py` → `/api/csrf/`
- `config/settings/base.py` → `DEFAULT_AUTHENTICATION_CLASSES`, `CSRF_COOKIE_*`
- `config/settings/dev.py` → `CSRF_COOKIE_HTTPONLY = False`
- `static/js/core/shared/csrf.js` (nuevo)
- `templates/base/partials/head.html` → carga `csrf.js`
- `templates/base/partials/scripts.html` → ya incluye `connection-status.js`

---

### 2.2 Rotación de sesión tras login (hallazgo #2)

**Problema:**  
No se llamaba a `request.session.cycle_key()` tras autenticar → riesgo de *session fixation* (un atacante que conoce el `sessionid` antes del login puede seguir usándolo después).

**Solución:**  
En `LoginView.post()` (tras `django_login()`):
```python
request.session.cycle_key()  # Invalida sessionid previo
```
También se llama en `TOTPVerifyLoginView` (login 2FA).

**Archivo:** `apps/authentication/views.py` → `LoginView`, `TOTPVerifyLoginView`.

---

### 2.3 Enlace de recuperación con esquema correcto (hallazgo #3)

**Problema:**  
En `services.py:361` el enlace se construía con `http://` hardcodeado:
```python
recovery_link = f"http://{host}/reset-password.html?token={token}"
```
Incluso en producción con `SECURE_SSL_REDIRECT = True`, el correo podía contener `http://`.

**Solución:**  
`recover_password()` ahora recibe el `request` completo y deduce el esquema:
```python
scheme = request.scheme if request else "http"
if not settings.DEBUG:
    scheme = "https"
recovery_link = f"{scheme}://{host}/reset-password.html?token={token}"
```
`ForgotPasswordView` pasa `request` en lugar de solo `host`.

**Archivos:** `apps/authentication/services.py`, `apps/authentication/views.py` → `ForgotPasswordView`.

---

### 2.4 Verificación de email en el registro (hallazgo #4)

**Problema:**  
No existía verificación de correo. Cualquiera podía registrarse (incl. profesionales) con email ajeno sin confirmarlo.

**Solución implementada:**

| Elemento | Detalle |
|----------|---------|
| Campo `email_verificado` en `Register` | `BooleanField(default=False)` — `True` solo para `paciente`; `profesional` queda `False` obligatoriamente. |
| Modelo `EmailVerificationToken` | Token único, expiración 24 h, un solo uso (`used=True`). |
| `register_user()` en `AuthService` | Si `rol == "profesional"` (o en producción global) → `email_verificado=False`, crea token, envía email con enlace `/verify-email.html?token=…`. |
| Endpoint `POST /api/verify-email/` (`VerifyEmailView`) | Valida token, marca `email_verificado=True`, invalida token. |
| `login_user()` | Rechaza login si `rol == "profesional"` y `email_verificado == False` (403 + mensaje). |
| Plantilla email | Incluye botón “Verificar mi correo” y enlace plano como fallback. |

**Archivos:**
- `apps/authentication/models.py` → `Register.email_verificado`, `EmailVerificationToken`
- `apps/authentication/repositories.py` → métodos `create_email_verification_token`, `validate_email_verification_token`, `mark_email_verified`
- `apps/authentication/services.py` → `register_user`, `_create_and_send_verification_email`
- `apps/authentication/serializers.py` → `VerifyEmailSerializer`
- `apps/authentication/views.py` → `VerifyEmailView`
- `apps/authentication/urls.py` → `/api/verify-email/`

---

### 2.5 Content-Security-Policy (CSP) (hallazgo #5)

**Problema:**  
`SecurityHeadersMiddleware` solo definía cabeceras “legacy” (`X-XSS-Protection`, etc.). Sin CSP no hay defensa moderna contra XSS / inyección de scripts.

**Solución:**  
Middleware actualizado (`apps/core/middleware/security_headers.py`) añade cabecera `Content-Security-Policy` con política restrictiva pero compatible:

```text
default-src 'self';
script-src 'self' 'unsafe-inline' https://sandbox.wompi.co https://production.wompi.co https://accounts.google.com https://apis.google.com;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' data: https://fonts.gstatic.com;
img-src 'self' data: https:;
connect-src 'self' https://sandbox.wompi.co https://production.wompi.co https://accounts.google.com https://oauth2.googleapis.com;
frame-src 'self' https://sandbox.wompi.co https://production.wompi.co https://accounts.google.com;
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
```

- En `DEBUG=True` → `Content-Security-Policy-Report-Only` (no rompe, solo reporta en consola).
- En producción → `Content-Security-Policy` enforce.
- Controlable vía `settings.CSP_ENABLED` (default `True`).

**Archivo:** `apps/core/middleware/security_headers.py`.

---

### 2.6 Autenticación de dos factores (2FA / TOTP) opcional (hallazgo #6)

**Problema:**  
No existía segundo factor para roles con acceso a datos clínicos (`admin`, `profesional`).

**Solución (alcance Mínimo Viable):**

| Componente | Descripción |
|------------|-------------|
| Modelo `TOTPDevice` | `OneToOneField(Register)`, `secret` (base32), `confirmed`, `last_used`. Compatible RFC 6238 (Google Authenticator, Authy, etc.). |
| `AuthService` métodos TOTP | `create_totp_device()`, `get_totp_provisioning_uri()`, `get_totp_qr_code_svg()`, `verify_totp_token()`, `confirm_totp_device()`, `disable_totp_device()`, `is_totp_enabled()`, `require_totp_for_role()`. |
| Endpoints REST (protegidos con `IsAuthenticated`) | `GET /api/totp/setup` → genera secreto + QR SVG; `POST /api/totp/confirm` → verifica primer token y marca `confirmed=True`; `POST /api/totp/disable` → requiere contraseña actual; `GET /api/totp/status` → estado actual. |
| Login con 2FA | Si `is_totp_enabled(user_id)` → `LoginView` guarda `pending_2fa_user_id` en sesión, responde `requires_2fa: true`. Frontend muestra modal → `POST /api/totp/verify-login` verifica token → completa `django_login()` y rota sesión. |
| Obligatoriedad por rol | `require_totp_for_role(role)` devuelve `True` para `admin` y `profesional`. En UI se puede forzar activación en primer login. |

**Dependencias nuevas:** `pyotp`, `qrcode`, `qrcode[pil]` (añadir a `requirements.txt`).

**Archivos nuevos/modificados:**
- `apps/authentication/models.py` → `TOTPDevice`
- `apps/authentication/authentication.py` (existente)
- `apps/authentication/services.py` → métodos TOTP
- `apps/authentication/repositories.py` → métodos TOTP
- `apps/authentication/serializers.py` → `TOTPSetupSerializer`, `TOTPVerifySerializer`, `TOTPDisableSerializer`
- `apps/authentication/views.py` → `TOTPSetupView`, `TOTPConfirmView`, `TOTPDisableView`, `TOTPStatusView`, `TOTPVerifyLoginView`
- `apps/authentication/urls.py` → rutas `/api/totp/*`
- `apps/authentication/views.py` → `LoginView` detecta 2FA y responde `requires_2fa: true`

---

## 3. Resumen de archivos creados / modificados

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `apps/authentication/authentication.py` | **Nuevo** | `CsrfEnforcedSessionAuthentication`, `CsrfExemptSessionAuthentication` |
| `apps/authentication/views.py` | **Modificado** | `CsrfTokenView`, `LoginView` (django_login + cycle_key + 2FA), `VerifyEmailView`, `TOTPSetupView`, `TOTPConfirmView`, `TOTPDisableView`, `TOTPStatusView`, `TOTPVerifyLoginView`, `ForgotPasswordView` (pasa `request`) |
| `apps/authentication/urls.py` | **Modificado** | Rutas `/csrf/`, `/verify-email/`, `/totp/*` |
| `apps/authentication/services.py` | **Modificado** | `recover_password(request)`, `register_user(request, email_verificado)`, `_create_and_send_verification_email()`, métodos TOTP completos |
| `apps/authentication/repositories.py` | **Modificado** | `create_user(email_verificado)`, métodos `EmailVerificationToken` y `TOTPDevice` |
| `apps/authentication/models.py` | **Modificado** | `Register.email_verificado`, `EmailVerificationToken`, `TOTPDevice` |
| `apps/authentication/serializers.py` | **Modificado** | `VerifyEmailSerializer`, `TOTPSetupSerializer`, `TOTPVerifySerializer`, `TOTPDisableSerializer` |
| `apps/authentication/backends.py` | Existente | `EmailBackend` (usado por `django_login`) |
| `apps/core/middleware/security_headers.py` | **Modificado** | CSP completo + Report-Only en dev |
| `apps/core/middleware/security_headers.py` | **Modificado** | CSP + cabeceras existentes |
| `config/settings/base.py` | **Modificado** | `DEFAULT_AUTHENTICATION_CLASSES`, `CSRF_COOKIE_*`, `CSP_ENABLED` |
| `config/settings/dev.py` | **Modificado** | `CSRF_COOKIE_HTTPONLY = False` |
| `config/settings/prod.py` | Existente | Ya tenía HSTS, cookies seguras, validación `SECRET_KEY` |
| `static/js/core/shared/csrf.js` | **Nuevo** | `fetchWithCsrf()`, `initCsrfToken()`, `getCsrfToken()` |
| `static/js/core/shared/connection-status.js` | Preexistente | Manejo offline/servidor caído/chatbot |
| `static/css/components/components.css` | Modificado | Estilos para `ConnectionErrorCard` y `error-bubble` |
| `templates/base/partials/head.html` | Modificado | Carga `csrf.js`, `components.css` |
| `templates/base/partials/scripts.html` | Preexistente | Ya incluye `connection-status.js` |
| `requirements.txt` | Pendiente | Añadir `pyotp>=2.9`, `qrcode>=7.4`, `qrcode[pil]>=7.4` |

---

## 4. Cómo probar los cambios localmente

```bash
# 1. Instalar dependencias nuevas
pip install pyotp>=2.9 qrcode>=7.4 "qrcode[pil]>=7.4"

# 2. Migraciones (nuevos modelos)
python manage.py makemigrations authentication
python manage.py migrate

# 3. Ejecutar servidor dev
python manage.py runserver

# 4. Probar flujo CSRF
# - Abrir DevTools → Network → hacer login → verificar header X-CSRFToken en peticiones POST
# - Verificar que sin token falla con 403 "CSRF token inválido o faltante"

# 5. Probar 2FA
# - Registrar usuario profesional → verificar email → login → GET /api/totp/setup → escanear QR → POST /api/totp/confirm con token → login nuevo pide 2FA

# 6. Probar CSP
# - En dev: abrir consola → buscar avisos "Content Security Policy Report-Only"
# - En prod: cabeceras CSP enforce (sin Report-Only)

# 7. Verificar rotación de sesión
# - Antes de login: anotar sessionid (cookie sessionid)
# - Login → verificar que sessionid cambió (cycle_key)

# 7. Verificar enlace recuperación
# - Solicitar recuperación en dev → correo usa http://
# - En prod (DEBUG=False) → correo usa https://
```

---

## 5. Referencias y dependencias externas

| Librería | Versión mínima | Uso |
|----------|----------------|-----|
| `pyotp` | 2.9 | Generación/verificación TOTP (RFC 6238) |
| `qrcode` | 7.4 | Generación de QR SVG para provisión TOTP |
| `qrcode[pil]` | 7.4 | Backend Pillow para renderizado QR |
| `django` | 4.2+ | Framework base (ya incluido) |
| `djangorestframework` | 3.14+ | DRF (ya incluido) |

---

## 6. Notas para el equipo de producto

- **Email verification** es obligatorio para *profesionales* desde ya. Pacientes pueden registrarse sin verificar, pero se recomienda activar `email_verificado=False` global en producción cambiando una línea en `services.py`.
- **2FA** es opcional por ahora (`require_totp_for_role` devuelve `True` para admin/profesional pero no bloquea el login si no está configurado). Para hacerlo obligatorio, en `LoginView` cambiar la lógica a: si `require_totp_for_role(rol)` y no `is_totp_enabled` → responder `requires_2fa_setup: true` y redirigir a pantalla de configuración 2FA antes de permitir acceso.
- **CSP** está en *Report-Only* en desarrollo. Antes de pasar a producción, revisar consola de navegador en todas las páginas y ajustar `script-src`, `connect-src`, etc. si hay bloqueos legítimos.
- **CSRF**: el helper `fetchWithCsrf()` está listo para usar. Migrar llamadas `fetch()` existentes en `static/js/modules/**/*.js` reemplazando `fetch(...)` por `fetchWithCsrf(...)` o importar `window.PsyAICsrf.fetch`. Como referencia, `chatbot.js` ya usa `credentials: 'include'` y ahora heredará el header automáticamente si se usa el wrapper.
- **Rotación de sesión** y **login real Django** garantizan que `request.user` esté poblado en vistas DRF, lo que permite futuras mejoras (p. ej. permisos basados en `request.user` en lugar de `request.session`).

---

## 7. Checklist de despliegue a producción

- [ ] `pip install -r requirements.txt` (incluye pyotp, qrcode, Pillow)
- [ ] `python manage.py migrate` (aplica modelos `EmailVerificationToken`, `TOTPDevice`)
- [ ] Variables de entorno: `SECRET_KEY` fuerte, `DEBUG=False`, `ALLOWED_HOSTS`, `CORS_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `EMAIL_*`, `WOMPI_*`, `GOOGLE_*`
- [ ] `CSP_ENABLED=True` (default) → cabecera enforce
- [ ] `CSRF_COOKIE_HTTPONLY=True` (default en `prod.py`)
- [ ] `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True` (ya en `prod.py`)
- [ ] HSTS activado (`SECURE_HSTS_SECONDS=31536000`)
- [ ] Certificados TLS válidos (Let's Encrypt o proveedor)
- [ ] Probar flujo completo: registro → verificación email → login → 2FA setup → login con 2FA
- [ ] Verificar cabeceras con `curl -I https://dominio.com` → CSP, HSTS, X-Frame-Options, etc.
- [ ] Escaneo de vulnerabilidades (OWASP ZAP, Snyk, etc.) post-despliegue

---

*Documento generado automáticamente como parte de la iteración de hardening de seguridad. Mantener actualizado ante cualquier cambio en la arquitectura de autenticación/autorización.*

---
## 8. WhatsApp (Twilio) — Consideraciones de seguridad

| Aspecto | Recomendación |
|---------|---------------|
| **Credenciales** | `TWILIO_SID` y `TWILIO_TOKEN` solo en `.env` de producción (nunca en repo). Rotar periódicamente en Twilio Console. |
| **WHATSAPP_ENABLED** | Activar solo cuando credenciales estén listas; valor parseado case‑insensitive (`true/1/yes`). |
| **Validación de firma** | Webhook usa `twilio.request_validator.RequestValidator` con `TWILIO_TOKEN` y `TWILIO_WEBHOOK_URL` exacta. Peticiones con firma inválida → 403. |
| **HTTPS obligatorio** | `TWILIO_WEBHOOK_URL` debe ser `https://` con certificado válido; Twilio rechaza HTTP en producción. |
| **Plantillas aprobadas** | Solo `ContentSid` de plantillas aprobadas por Meta pueden usarse fuera de la ventana de 24 h. Variables `TWILIO_TPL_*` deben coincidir con las aprobadas. |
| **Opt‑out (STOP/BAJA/UNSUBSCRIBE)** | Webhook desactiva `whatsappConsentimiento` y fuerza `canalNotificacion=email`. Responde al usuario confirmando baja. |
| **Rate limits** | Twilio impone límites por número remitente; monitorizar `providerMsgId` y estado (`delivered/failed/undelivered`) vía status callback opcional. |
| **Datos sensibles** | Nunca loguear `TWILIO_TOKEN` ni cuerpos completos de mensajes. Logs solo SID y estado. |
| **Pruebas** | Comando `python manage.py probar_whatsapp +57…` usa credenciales reales; en CI usar `WHATSAPP_ENABLED=False` (DummyProvider). |
| **CSP / Headers** | Endpoints `/api/whatsapp/webhook/` y `/api/whatsapp/status/` están bajo CSP `connect-src 'self'` y no exponen datos de usuario. |