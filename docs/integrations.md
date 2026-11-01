# Integraciones Externas — PsyAI Connect

> **Resumen:** Documenta las integraciones con servicios de terceros implementadas en el proyecto: Google Gemini (IA), Twilio (WhatsApp), Google OAuth (allauth), correo transaccional (SMTP) y pagos manuales con evidencia.  
> **Audiencia:** desarrolladores y DevOps que configuran o mantienen las integraciones.  
> **Estado:** refleja el código real de `apps/chatbot/`, `apps/core/`, `apps/authentication/`, `apps/billing/` y `config/settings/`.

---

## 1. Resumen de integraciones

| Integración | Proveedor | Propósito | Archivo clave | Estado |
|-------------|-----------|-----------|---------------|--------|
| **Chatbot IA** | Google Gemini API | Respuestas del chatbot de triaje y apoyo emocional | `apps/chatbot/services.py` | Activa |
| **Mensajería WhatsApp** | Twilio | Notificaciones de citas, recordatorios, opt-in/opt-out | `apps/core/whatsapp.py`, `apps/core/notifier.py` | Activa (modo simulado si no hay credenciales) |
| **Autenticación social** | Google (OAuth 2.0 vía allauth) | Login con cuenta de Google | `apps/authentication/adapters.py` | Activa |
| **Correo transaccional** | SMTP (configurable, p. ej. Brevo) | Bienvenida, facturas, citas, alertas de riesgo, recuperación de contraseña | `apps/core/services.py`, `apps/core/notifier.py`, `apps/authentication/services.py` | Activa (SMTP) |
| **Pagos** | Manual (evidencia de pago) | Creación y confirmación de facturas con comprobante adjunto | `apps/billing/services.py`, `apps/billing/views.py` | Activa (sin pasarela automática) |
| **Boletín informativo** | Interno (base de datos) | Suscripción y envío de tips de bienestar emocional | `apps/core/services.py` | Activa |

> **Nota sobre Wompi:** El proyecto eliminó los campos de Wompi en la migración `0004_remove_wompi_fields_add_fechapago`. Actualmente los pagos se gestionan de forma manual: el profesional crea la factura, el paciente adjunta una evidencia (imagen/PDF) y el profesional confirma el pago. No hay pasarela de pago automática integrada.

---

## 2. Google Gemini — Chatbot de IA

Archivo principal: `apps/chatbot/services.py` → `ChatbotService`

### 2.1. Funcionalidad

El chatbot de triaje psicológico envía mensajes del usuario a Google Gemini y devuelve una respuesta empática, con detección de riesgo emocional y fallback local si el servicio no está disponible.

### 2.2. Flujo

```
Paciente → POST /api/chatbot/enviar → ChatbotViewSet.create
                                      │
                                      ▼
                              ChatbotService.build_response()
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
    Detección de riesgo       Llamada a Gemini        Fallback local
    (términos alto/medio)     (rotación de API keys)    si Gemini falla
              │                       │                       │
              └───────────────────────┴───────────────────────┘
                                      │
                                      ▼
                            Guarda en ConversacionesChatbot
                                      │
                                      ▼
                            Respuesta JSON al frontend
```

### 2.3. Variables de entorno

| Variable | Descripción | Obligatoria | Default |
|----------|-------------|-------------|---------|
| `GEMINI_API_KEY` | API key principal de Gemini | Sí | — |
| `GEMINI_API_KEYS` | Keys adicionales separadas por coma (rotación) | No | — |
| `GEMINI_MODEL` | Modelo de Gemini | No | `gemini-3.5-flash-lite` |
| `GEMINI_FALLBACK_MODEL` | Modelo de respaldo si el principal falla | No | `gemma-4-26b-a4b-it` |
| `GEMINI_THINKING_LEVEL` | Nivel de razonamiento (`low/medium/high/none`) | No | `low` |
| `GEMINI_REQUEST_TIMEOUT_CONNECT` | Timeout de conexión (s) | No | `3` |
| `GEMINI_REQUEST_TIMEOUT_READ` | Timeout de lectura intento 1 (s) | No | `8` |
| `GEMINI_MIN_READ_TIMEOUT_SECONDS` | Read timeout mínimo garantizado (s) | No | `3` |
| `GEMINI_RETRIES` | Reintentos ante error de red/timeout | No | `2` |
| `GEMINI_RETRY_BASE_DELAY` | Retraso base entre reintentos (s) | No | `0.2` |
| `GEMINI_TOTAL_DEADLINE_SECONDS` | Presupuesto total para la llamada (s) | No | `10` |

### 2.4. Rotación de API keys

`ChatbotService._call_gemini_with_rotation()` itera sobre las keys disponibles. Si una key retorna `429` (cuota agotada) y hay más keys, rota a la siguiente. Si se agotan todas, prueba el modelo de respaldo (`GEMINI_FALLBACK_MODEL`). Si todo falla, se activa `_build_local_fallback()` con `success: true` y `fallback: true`.

### 2.5. Sanitización de PII

Antes de enviar a Gemini, `ChatbotService._sanitize_text()` enmascara correos electrónicos, teléfonos colombianos, números de documento (CC, CE, TI, pasaporte) y tarjetas de crédito. Se aplica al historial y al mensaje actual.

---

## 3. Twilio — WhatsApp

Archivos principales:
- `apps/core/whatsapp.py` → `WhatsAppProvider`, `TwilioProvider`, `DummyProvider`, `get_whatsapp_provider()`
- `apps/core/webhooks.py` → `WhatsAppWebhook`, `WhatsAppStatusCallback`
- `apps/core/notifier.py` → `NotificationService`

### 3.1. Proveedores

| Proveedor | Cuándo se usa | Comportamiento |
|-----------|---------------|----------------|
| `TwilioProvider` | `WHATSAPP_ENABLED=True` y credenciales completas | Envía real vía Twilio API |
| `DummyProvider` | `WHATSAPP_ENABLED=False` o credenciales incompletas | Modo simulado, loguea sin enviar |

`get_whatsapp_provider()` retorna `TwilioProvider` si `WHATSAPP_ENABLED` es True, de lo contrario `DummyProvider`.

### 3.2. Variables de entorno

| Variable | Descripción | Obligatoria | Default |
|----------|-------------|-------------|---------|
| `WHATSAPP_ENABLED` | Activa envío real (`true/1/yes`) | No | `False` |
| `TWILIO_SID` | Account SID de Twilio | Si `WHATSAPP_ENABLED=true` | — |
| `TWILIO_TOKEN` | Auth Token de Twilio | Si `WHATSAPP_ENABLED=true` | — |
| `TWILIO_WHATSAPP_FROM` | Número remitente (`whatsapp:+...`) | Si `WHATSAPP_ENABLED=true` | — |
| `TWILIO_WEBHOOK_URL` | URL pública del webhook entrante | No | — |
| `TWILIO_STATUS_CALLBACK_URL` | URL para callbacks de estado | Opcional | — |
| `TWILIO_TPL_RECORDATORIO` | Content SID plantilla recordatorio cita | No | — |
| `TWILIO_TPL_CONFIRMACION` | Content SID plantilla confirmación cita | No | — |
| `TWILIO_TPL_CANCELACION` | Content SID plantilla cancelación cita | No | — |
| `TWILIO_TPL_MENSAJE_PRO` | Content SID plantilla mensaje profesional | No | — |

### 3.3. Webhooks

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/paciente/whatsapp/webhook/` | `POST` | Webhook entrante de Twilio. Verifica firma HMAC (`X-Twilio-Signature`). Maneja opt-out (`STOP`, `BAJA`, `UNSUBSCRIBE`). |
| WhatsApp Status Callback | `POST` | Actualiza estado de notificaciones (`sent`, `delivered`, `failed`, `undelivered`) por `providerMsgId`. |

### 3.4. Notificaciones al paciente

`NotificationService.notificar_paciente()` en `apps/core/notifier.py` envía por email y/o WhatsApp según las preferencias del paciente (`canalNotificacion`: `email`, `whatsapp`, `ambos`, `ninguno`). Tipos soportados: `recordatorio_cita`, `confirmacion_cita`, `cancelacion_cita`, `mensaje_profesional`.

Registra cada intento en `Notificaciones` (tabla de `apps/scheduling/models.py`) con `estado`, `canal`, `errorDetalle` y `providerMsgId`.

---

## 4. Google OAuth — Autenticación social

Archivo principal: `apps/authentication/adapters.py` → `SocialAccountAdapter`

### 4.1. Configuración

Configurado en `config/settings/base.py` con `django-allauth` y el proveedor Google:
- `allauth.socialaccount.providers.google` en `INSTALLED_APPS`
- `SocialAccountAdapter` personalizado

### 4.2. Comportamiento

| Aspecto | Detalle |
|---------|---------|
| Rol asignado | Siempre `paciente` (fuerza `rol='paciente'` independientemente del proveedor) |
| Contraseña | Se genera `uuid.uuid4().hex` (contraseña inutilizable, login solo vía OAuth) |
| Nombre | Desde `extra_data["name"]` o `extra_data["first_name"]` |
| Foto de perfil | Desde `extra_data["picture"]` si existe |
| Perfil paciente | Se crea automáticamente `PerfilPaciente` con `consentimientoDatos=True` y `consentimiento_chatbot=True` |
| Sesión | Se configura vía `_setup_session()` con `idUsuario`, `nombre`, `rol`, `fotoPerfil` |

### 4.3. Variables de entorno

| Variable | Descripción | Obligatoria |
|----------|-------------|-------------|
| `GOOGLE_CLIENT_ID` | Client ID de Google OAuth | No (requerido para usar login social) |
| `GOOGLE_CLIENT_SECRET` | Client Secret de Google OAuth | No (requerido para usar login social) |

---

## 5. Correo transaccional (SMTP)

Archivos principales:
- `apps/core/services.py` → `CoreService.send_welcome_email()`, `subscribe_newsletter()`
- `apps/core/notifier.py` → `NotificationService._build_email()` (envía via `send_mail`)
- `apps/billing/services.py` → `InvoiceService` (envía notificaciones de factura)
- `apps/scheduling/services.py` → `AppointmentService._notify()` (envía notificaciones de cita)
- `apps/authentication/services.py` → `AuthService` (emails de verificación y recuperación)
- `apps/chatbot/services.py` → `_send_risk_email()` (alertas de riesgo)
- `apps/admin_panel/services.py` → emails de suspensión de cuenta

### 5.1. Backend

Django usa `django.core.mail.backends.smtp.EmailBackend` por defecto. En desarrollo, si no hay `EMAIL_HOST_USER`, usa `console.EmailBackend` (imprime en terminal).

### 5.2. Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `EMAIL_BACKEND` | Backend de Django | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | Servidor SMTP | `smtp.gmail.com` |
| `EMAIL_PORT` | Puerto SMTP | `587` |
| `EMAIL_USE_TLS` | Usar TLS | `True` |
| `EMAIL_HOST_USER` | Usuario SMTP | — |
| `EMAIL_HOST_PASSWORD` | Contraseña SMTP | — |
| `DEFAULT_FROM_EMAIL` | Remitente | `PsyAI Connect <noreply@psyaiconnect.com>` |
| `SITE_URL` | URL base para enlaces en emails | `http://localhost:8000` |

> **Nota sobre Brevo:** El README menciona Brevo como servicio de correos transaccionales, pero el código implementa envío vía SMTP estándar de Django. Se puede configurar Brevo como servidor SMTP definiendo `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` con las credenciales de Brevo.

### 5.3. Plantillas de email

| Plantilla | Uso |
|-----------|-----|
| `templates/emails/newsletter_welcome.html` | Correo de bienvenida al boletín |
| `templates/emails/factura_notificacion.html` | Notificación de factura |
| `templates/emails/cita_notificacion.html` | Notificación de cita |
| `templates/emails/alerta_riesgo.html` | Alerta de riesgo emocional (chatbot) |
| `templates/emails/password_recovery.html` | Recuperación de contraseña |
| `templates/emails/cuenta_bloqueada.html` | Cuenta suspendida |
| `templates/emails/pago_confirmado_webhook.html` | Confirmación de pago |

---

## 6. Pagos — Confirmación manual con evidencia

Archivos principales:
- `apps/billing/services.py` → `InvoiceService`
- `apps/billing/views.py` → `FacturaListView`, `FacturaConfirmarPagoView`, `FacturaEvidenciaView`
- `apps/billing/models.py` → `Facturas`
- `apps/professionals/models.py` → `ProfessionalPaymentInfo`

### 6.1. Flujo de pago

1. **Crear factura:** `POST /api/facturas` (solo profesional). Requiere `items`, `idPaciente`, `metodoPago`, `evidencia` (archivo adjunto), `fechaPago`, `referencia`, `notas`.
2. **Validación de evidencia:** Se valida extensión (`jpg`, `jpeg`, `png`, `webp`, `pdf`) y tamaño (máx. 5 MB) mediante `validate_file_upload()` en `apps/core/utils.py`.
3. **Confirmar pago:** `POST /api/facturas/<id>/confirmar-pago` (solo profesional dueño). Marca la factura como confirmada.
4. **Ver evidencia:** `GET /api/facturas/<id>/evidencia` — sirve el archivo adjunto.

### 6.2. Métodos de pago

Definidos en `Facturas.METODO_PAGO_CHOICES` (apps/billing/models.py). Incluyen transferencia, Nequi, Bre-B, efectivo, etc.

### 6.3. Información de pago del profesional

Modelo `ProfessionalPaymentInfo`:
- `qr_image`: Imagen QR para pagos
- `mensaje_texto`: Número de cuenta, Nequi, llaves Bre-B, etc.

> **Nota:** No hay integración con pasarela de pago automática (Wompi fue removido). Los pagos se confirman manualmente por el profesional tras verificar la evidencia adjunta.

---

## 7. Boletín informativo (Newsletter)

Archivo: `apps/core/services.py` → `CoreService`

### 7.1. Funcionalidad

- `subscribe_newsletter(email)`: Suscribe un correo al boletín. Valida el formato del email. Crea o reactiva un `NewsletterSubscriber`. Envía email de bienvenida si es nueva suscripción.
- `send_welcome_email(to_email)`: Envía correo de bienvenida con un tip de respiración (4-7-8).

### 7.2. Modelo

`NewsletterSubscriber` (apps/core/models.py): `email`, `is_active`, `fechaSuscripcion`.

---

## 8. Variables de entorno consolidadas

| Variable | Integración | Obligatoria | Default |
|----------|-------------|-------------|---------|
| `GEMINI_API_KEY` | Gemini | Sí | — |
| `GEMINI_API_KEYS` | Gemini | No | — |
| `GEMINI_MODEL` | Gemini | No | `gemini-3.5-flash-lite` |
| `GEMINI_FALLBACK_MODEL` | Gemini | No | `gemma-4-26b-a4b-it` |
| `GEMINI_THINKING_LEVEL` | Gemini | No | `low` |
| `GEMINI_REQUEST_TIMEOUT_CONNECT` | Gemini | No | `3` |
| `GEMINI_REQUEST_TIMEOUT_READ` | Gemini | No | `8` |
| `GEMINI_MIN_READ_TIMEOUT_SECONDS` | Gemini | No | `3` |
| `GEMINI_RETRIES` | Gemini | No | `2` |
| `GEMINI_RETRY_BASE_DELAY` | Gemini | No | `0.2` |
| `GEMINI_TOTAL_DEADLINE_SECONDS` | Gemini | No | `10` |
| `WHATSAPP_ENABLED` | Twilio | No | `False` |
| `TWILIO_SID` | Twilio | Si `WHATSAPP_ENABLED=true` | — |
| `TWILIO_TOKEN` | Twilio | Si `WHATSAPP_ENABLED=true` | — |
| `TWILIO_WHATSAPP_FROM` | Twilio | Si `WHATSAPP_ENABLED=true` | — |
| `TWILIO_WEBHOOK_URL` | Twilio | No | — |
| `TWILIO_STATUS_CALLBACK_URL` | Twilio | No | — |
| `TWILIO_TPL_RECORDATORIO` | Twilio | No | — |
| `TWILIO_TPL_CONFIRMACION` | Twilio | No | — |
| `TWILIO_TPL_CANCELACION` | Twilio | No | — |
| `TWILIO_TPL_MENSAJE_PRO` | Twilio | No | — |
| `GOOGLE_CLIENT_ID` | Google OAuth | No | — |
| `GOOGLE_CLIENT_SECRET` | Google OAuth | No | — |
| `EMAIL_HOST` | SMTP | No | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP | No | `587` |
| `EMAIL_USE_TLS` | SMTP | No | `True` |
| `EMAIL_HOST_USER` | SMTP | No | — |
| `EMAIL_HOST_PASSWORD` | SMTP | No | — |
| `DEFAULT_FROM_EMAIL` | SMTP | No | `PsyAI Connect <noreply@psyaiconnect.com>` |
| `SITE_URL` | General | No | `http://localhost:8000` |

---

## 9. Endpoints de integración

| Método | Endpoint | Integración | Permiso |
|--------|----------|-------------|---------|
| `POST` | `/api/chatbot/enviar` | Gemini | Autenticado + Paciente |
| `POST` | `/api/paciente/whatsapp/webhook/` | Twilio (webhook) | Público (firma HMAC) |
| `GET/POST` | `/api/auth/social/google/` | Google OAuth | Público |
| `GET/POST` | `/api/facturas` | Pagos (manual) | Autenticado |
| `POST` | `/api/facturas/<id>/confirmar-pago` | Pagos (manual) | Profesional |
| `GET` | `/api/facturas/<id>/evidencia` | Pagos (manual) | Autenticado |
| `POST` | `/api/newsletter/suscribir` | Newsletter | Público |

---

## 10. Archivos clave

| Ruta | Contenido |
|------|-----------|
| `apps/chatbot/services.py` | `ChatbotService`: llamada a Gemini, rotación de keys, fallback, sanitización PII |
| `apps/core/whatsapp.py` | `TwilioProvider`, `DummyProvider`, `get_whatsapp_provider()` |
| `apps/core/webhooks.py` | `WhatsAppWebhook`, `WhatsAppStatusCallback` |
| `apps/core/notifier.py` | `NotificationService`: notificaciones email/WhatsApp al paciente |
| `apps/core/services.py` | `CoreService`: newsletter, email de bienvenida |
| `apps/authentication/adapters.py` | `SocialAccountAdapter`: Google OAuth (forza rol paciente) |
| `apps/authentication/services.py` | `AuthService`: emails de verificación y recuperación |
| `apps/billing/services.py` | `InvoiceService`: creación, confirmación y envío de facturas |
| `apps/billing/views.py` | Vistas de facturas y confirmación de pago |
| `apps/billing/models.py` | `Facturas`, `ProfessionalPaymentInfo` |
| `apps/scheduling/services.py` | `AppointmentService`: notificaciones de cita |
| `apps/core/utils.py` | `validate_file_upload()`: validación de archivos adjuntos |

---

## 11. Ver también

- [`deployment.md`](deployment.md) — Variables de entorno y despliegue con Docker
- [`security.md`](security.md) — HMAC de webhooks, rate limiting, cookies seguras
- [`chatbot-ai.md`](chatbot-ai.md) — Detalle del chatbot con Gemini
- [`roles-and-permissions.md`](roles-and-permissions.md) — Permisos por endpoint de integración

---

## English Version

# External Integrations — PsyAI Connect

> **Summary:** Documents integrations with third-party services implemented in the project: Google Gemini (AI), Twilio (WhatsApp), Google OAuth (allauth), transactional email (SMTP) and manual payments with evidence.  
> **Audience:** developers and DevOps who configure or maintain integrations.  
> **Status:** reflects real code from `apps/chatbot/`, `apps/core/`, `apps/authentication/`, `apps/billing/` and `config/settings/`.

---

## 1. Integrations summary / Resumen de integraciones

| Integration | Provider | Purpose | Key file | Status |
|-------------|----------|---------|----------|--------|
| **Chatbot AI** | Google Gemini API | Chatbot triage and emotional support responses | `apps/chatbot/services.py` | Active |
| **WhatsApp messaging** | Twilio | Appointment notifications, reminders, opt-in/opt-out | `apps/core/whatsapp.py`, `apps/core/notifier.py` | Active (simulated mode if no credentials) |
| **Social authentication** | Google (OAuth 2.0 via allauth) | Login with Google account | `apps/authentication/adapters.py` | Active |
| **Transactional email** | SMTP (configurable, e.g. Brevo) | Welcome, invoices, appointments, risk alerts, password recovery | `apps/core/services.py`, `apps/core/notifier.py`, `apps/authentication/services.py` | Active (SMTP) |
| **Payments** | Manual (evidence) | Invoice creation and confirmation with attached proof | `apps/billing/services.py`, `apps/billing/views.py` | Active (no automatic gateway) |
| **Newsletter** | Internal (database) | Subscription and emotional well-being tips delivery | `apps/core/services.py` | Active |

> **Note about Wompi:** The project removed Wompi fields in migration `0004_remove_wompi_fields_add_fechapago`. Currently payments are managed manually: the professional creates the invoice, the patient attaches evidence (image/PDF) and the professional confirms payment. No automatic payment gateway is integrated.

---

## 2. Google Gemini — AI chatbot

Main file: `apps/chatbot/services.py` → `ChatbotService`

### 2.1. Functionality

The psychological triage chatbot sends user messages to Google Gemini and returns an empathetic response, with emotional risk detection and local fallback if the service is unavailable.

### 2.2. Flow

```
Patient → POST /api/chatbot/enviar → ChatbotViewSet.create
                                      │
                                      ▼
                              ChatbotService.build_response()
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
    Risk detection              Gemini call           Local fallback
    (high/medium terms)         (API key rotation)      if Gemini fails
              │                       │                       │
              └───────────────────────┴───────────────────────┘
                                      │
                                      ▼
                            Saves in ConversacionesChatbot
                                      │
                                      ▼
                            Returns JSON to frontend
```

### 2.3. Environment variables

| Variable | Description | Mandatory | Default |
|----------|-------------|-----------|---------|
| `GEMINI_API_KEY` | Main Gemini API key | Yes | — |
| `GEMINI_API_KEYS` | Additional keys separated by comma (rotation) | No | — |
| `GEMINI_MODEL` | Gemini model | No | `gemini-3.5-flash-lite` |
| `GEMINI_FALLBACK_MODEL` | Fallback model if main fails | No | `gemma-4-26b-a4b-it` |
| `GEMINI_THINKING_LEVEL` | Reasoning level (`low/medium/high/none`) | No | `low` |
| `GEMINI_REQUEST_TIMEOUT_CONNECT` | Connection timeout (s) | No | `3` |
| `GEMINI_REQUEST_TIMEOUT_READ` | Read timeout attempt 1 (s) | No | `8` |
| `GEMINI_MIN_READ_TIMEOUT_SECONDS` | Minimum guaranteed read timeout (s) | No | `3` |
| `GEMINI_RETRIES` | Retries on network error/timeout | No | `2` |
| `GEMINI_RETRY_BASE_DELAY` | Base delay between retries (s) | No | `0.2` |
| `GEMINI_TOTAL_DEADLINE_SECONDS` | Total budget for the call (s) | No | `10` |

### 2.4. API key rotation

`ChatbotService._call_gemini_with_rotation()` iterates over available keys. If a key returns `429` (quota exhausted) and more keys exist, rotates to the next one. If all keys exhausted, tries fallback model (`GEMINI_FALLBACK_MODEL`) if different from main. If everything fails, activates `_build_local_fallback()` with `success: true` and `fallback: true`.

### 2.5. PII sanitization

Before sending to Gemini, `ChatbotService._sanitize_text()` masks email addresses, Colombian phone numbers, document numbers (CC, CE, TI, passport) and credit cards. Applied to history and current message.

---

## 3. Twilio — WhatsApp

Main files:
- `apps/core/whatsapp.py` → `WhatsAppProvider`, `TwilioProvider`, `DummyProvider`, `get_whatsapp_provider()`
- `apps/core/webhooks.py` → `WhatsAppWebhook`, `WhatsAppStatusCallback`
- `apps/core/notifier.py` → `NotificationService`

### 3.1. Providers

| Provider | When used | Behavior |
|----------|-----------|----------|
| `TwilioProvider` | `WHATSAPP_ENABLED=True` and complete credentials | Real send via Twilio API |
| `DummyProvider` | `WHATSAPP_ENABLED=False` or incomplete credentials | Simulated mode, logs without sending |

`get_whatsapp_provider()` returns `TwilioProvider` if `WHATSAPP_ENABLED` is True, otherwise `DummyProvider`.

### 3.2. Environment variables

| Variable | Description | Mandatory | Default |
|----------|-------------|-----------|---------|
| `WHATSAPP_ENABLED` | Activates real send (`true/1/yes`) | No | `False` |
| `TWILIO_SID` | Twilio Account SID | If `WHATSAPP_ENABLED=true` | — |
| `TWILIO_TOKEN` | Twilio Auth Token | If `WHATSAPP_ENABLED=true` | — |
| `TWILIO_WHATSAPP_FROM` | Sender number (`whatsapp:+...`) | If `WHATSAPP_ENABLED=true` | — |
| `TWILIO_WEBHOOK_URL` | Public webhook URL | No | — |
| `TWILIO_STATUS_CALLBACK_URL` | Status callback URL | Optional | — |
| `TWILIO_TPL_RECORDATORIO` | Content SID for appointment reminder template | No | — |
| `TWILIO_TPL_CONFIRMACION` | Content SID for appointment confirmation template | No | — |
| `TWILIO_TPL_CANCELACION` | Content SID for appointment cancellation template | No | — |
| `TWILIO_TPL_MENSAJE_PRO` | Content SID for professional message template | No | — |

### 3.3. Webhooks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/paciente/whatsapp/webhook/` | `POST` | Incoming Twilio webhook. Verifies HMAC signature (`X-Twilio-Signature`). Handles opt-out (`STOP`, `BAJA`, `UNSUBSCRIBE`). |
| WhatsApp Status Callback | `POST` | Updates notification status (`sent`, `delivered`, `failed`, `undelivered`) by `providerMsgId`. |

### 3.4. Patient notifications

`NotificationService.notificar_paciente()` in `apps/core/notifier.py` sends by email and/or WhatsApp according to patient preferences (`canalNotificacion`: `email`, `whatsapp`, `ambos`, `ninguno`). Supported types: `recordatorio_cita`, `confirmacion_cita`, `cancelacion_cita`, `mensaje_profesional`.

Registers each attempt in `Notificaciones` (table of `apps/scheduling/models.py`) with `estado`, `canal`, `errorDetalle` and `providerMsgId`.

---

## 4. Google OAuth — Social authentication

Main file: `apps/authentication/adapters.py` → `SocialAccountAdapter`

### 4.1. Configuration

Configured in `config/settings/base.py` with `django-allauth` and Google provider:
- `allauth.socialaccount.providers.google` in `INSTALLED_APPS`
- Custom `SocialAccountAdapter`

### 4.2. Behavior

| Aspect | Detail |
|--------|--------|
| Assigned role | Always `paciente` (forces `rol='paciente'` regardless of provider) |
| Password | `uuid.uuid4().hex` generated (unusable password, login only via OAuth) |
| Name | From `extra_data["name"]` or `extra_data["first_name"]` |
| Profile picture | From `extra_data["picture"]` if exists |
| Patient profile | Automatically creates `PerfilPaciente` with `consentimientoDatos=True` and `consentimiento_chatbot=True` |
| Session | Configured via `_setup_session()` with `idUsuario`, `nombre`, `rol`, `fotoPerfil` |

### 4.3. Environment variables

| Variable | Description | Mandatory |
|----------|-------------|-----------|
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | No (required to use social login) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | No (required to use social login) |

---

## 5. Transactional email (SMTP)

Main files:
- `apps/core/services.py` → `CoreService.send_welcome_email()`, `subscribe_newsletter()`
- `apps/core/notifier.py` → `NotificationService._build_email()` (sends via `send_mail`)
- `apps/billing/services.py` → `InvoiceService` (sends invoice notifications)
- `apps/scheduling/services.py` → `AppointmentService._notify()` (sends appointment notifications)
- `apps/authentication/services.py` → `AuthService` (verification and recovery emails)
- `apps/chatbot/services.py` → `_send_risk_email()` (risk alerts)
- `apps/admin_panel/services.py` → account suspension emails

### 5.1. Backend

Django uses `django.core.mail.backends.smtp.EmailBackend` by default. In development, if no `EMAIL_HOST_USER`, uses `console.EmailBackend` (prints to terminal).

### 5.2. Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_BACKEND` | Django email backend | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | SMTP server | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_USE_TLS` | Use TLS | `True` |
| `EMAIL_HOST_USER` | SMTP user | — |
| `EMAIL_HOST_PASSWORD` | SMTP password | — |
| `DEFAULT_FROM_EMAIL` | Sender | `PsyAI Connect <noreply@psyaiconnect.com>` |
| `SITE_URL` | Base URL for email links | `http://localhost:8000` |

> **Note about Brevo:** The README mentions Brevo as transactional email service, but the code implements email sending via standard Django SMTP. Brevo can be configured as SMTP server by defining `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` with Brevo credentials.

### 5.3. Email templates

| Template | Use |
|----------|-----|
| `templates/emails/newsletter_welcome.html` | Newsletter welcome email |
| `templates/emails/factura_notificacion.html` | Invoice notification |
| `templates/emails/cita_notificacion.html` | Appointment notification |
| `templates/emails/alerta_riesgo.html` | Emotional risk alert (chatbot) |
| `templates/emails/password_recovery.html` | Password recovery |
| `templates/emails/cuenta_bloqueada.html` | Account suspended |
| `templates/emails/pago_confirmado_webhook.html` | Payment confirmation |

---

## 6. Payments — Manual confirmation with evidence

Main files:
- `apps/billing/services.py` → `InvoiceService`
- `apps/billing/views.py` → `FacturaListView`, `FacturaConfirmarPagoView`, `FacturaEvidenciaView`
- `apps/billing/models.py` → `Facturas`
- `apps/professionals/models.py` → `ProfessionalPaymentInfo`

### 6.1. Payment flow

1. **Create invoice:** `POST /api/facturas` (professional only). Requires `items`, `idPaciente`, `metodoPago`, `evidencia` (attached file), `fechaPago`, `referencia`, `notas`.
2. **Evidence validation:** Validates extension (`jpg`, `jpeg`, `png`, `webp`, `pdf`) and size (max 5 MB) via `validate_file_upload()` in `apps/core/utils.py`.
3. **Confirm payment:** `POST /api/facturas/<id>/confirmar-pago` (professional owner only). Marks invoice as confirmed.
4. **View evidence:** `GET /api/facturas/<id>/evidencia` — serves attached file.

### 6.2. Payment methods

Defined in `Facturas.METODO_PAGO_CHOICES` (apps/billing/models.py). Includes transfer, Nequi, Bre-B, cash, etc.

### 6.3. Professional payment information

Model `ProfessionalPaymentInfo`:
- `qr_image`: QR image for payments
- `mensaje_texto`: Account number, Nequi, Bre-B keys, etc.

> **Note:** No automatic payment gateway integration (Wompi was removed). Payments are manually confirmed by the professional after verifying attached evidence.

---

## 7. Newsletter

Main file: `apps/core/services.py` → `CoreService`

### 7.1. Functionality

- `subscribe_newsletter(email)`: Subscribes an email to the newsletter. Validates email format. Creates or reactivates a `NewsletterSubscriber`. Sends welcome email if new subscription.
- `send_welcome_email(to_email)`: Sends welcome email with a breathing tip (4-7-8).

### 7.2. Model

`NewsletterSubscriber` (apps/core/models.py): `email`, `is_active`, `fechaSuscripcion`.

---

## 8. Consolidated environment variables

| Variable | Integration | Mandatory | Default |
|----------|-------------|-----------|---------|
| `GEMINI_API_KEY` | Gemini | Yes | — |
| `GEMINI_API_KEYS` | Gemini | No | — |
| `GEMINI_MODEL` | Gemini | No | `gemini-3.5-flash-lite` |
| `GEMINI_FALLBACK_MODEL` | Gemini | No | `gemma-4-26b-a4b-it` |
| `GEMINI_THINKING_LEVEL` | Gemini | No | `low` |
| `GEMINI_REQUEST_TIMEOUT_CONNECT` | Gemini | No | `3` |
| `GEMINI_REQUEST_TIMEOUT_READ` | Gemini | No | `8` |
| `GEMINI_MIN_READ_TIMEOUT_SECONDS` | Gemini | No | `3` |
| `GEMINI_RETRIES` | Gemini | No | `2` |
| `GEMINI_RETRY_BASE_DELAY` | Gemini | No | `0.2` |
| `GEMINI_TOTAL_DEADLINE_SECONDS` | Gemini | No | `10` |
| `WHATSAPP_ENABLED` | Twilio | No | `False` |
| `TWILIO_SID` | Twilio | If `WHATSAPP_ENABLED=true` | — |
| `TWILIO_TOKEN` | Twilio | If `WHATSAPP_ENABLED=true` | — |
| `TWILIO_WHATSAPP_FROM` | Twilio | If `WHATSAPP_ENABLED=true` | — |
| `TWILIO_WEBHOOK_URL` | Twilio | No | — |
| `TWILIO_STATUS_CALLBACK_URL` | Twilio | No | — |
| `TWILIO_TPL_RECORDATORIO` | Twilio | No | — |
| `TWILIO_TPL_CONFIRMACION` | Twilio | No | — |
| `TWILIO_TPL_CANCELACION` | Twilio | No | — |
| `TWILIO_TPL_MENSAJE_PRO` | Twilio | No | — |
| `GOOGLE_CLIENT_ID` | Google OAuth | No | — |
| `GOOGLE_CLIENT_SECRET` | Google OAuth | No | — |
| `EMAIL_HOST` | SMTP | No | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP | No | `587` |
| `EMAIL_USE_TLS` | SMTP | No | `True` |
| `EMAIL_HOST_USER` | SMTP | No | — |
| `EMAIL_HOST_PASSWORD` | SMTP | No | — |
| `DEFAULT_FROM_EMAIL` | SMTP | No | `PsyAI Connect <noreply@psyaiconnect.com>` |
| `SITE_URL` | General | No | `http://localhost:8000` |

---

## 9. Integration endpoints

| Method | Endpoint | Integration | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/chatbot/enviar` | Gemini | Authenticated + Patient |
| `POST` | `/api/paciente/whatsapp/webhook/` | Twilio (webhook) | Public (HMAC signature) |
| `GET/POST` | `/api/auth/social/google/` | Google OAuth | Public |
| `GET/POST` | `/api/facturas` | Payments (manual) | Authenticated |
| `POST` | `/api/facturas/<id>/confirmar-pago` | Payments (manual) | Professional |
| `GET` | `/api/facturas/<id>/evidencia` | Payments (manual) | Authenticated |
| `POST` | `/api/newsletter/suscribir` | Newsletter | Public |

---

## 10. Key files

| Path | Content |
|------|-----------|
| `apps/chatbot/services.py` | `ChatbotService`: Gemini call, key rotation, fallback, PII sanitization |
| `apps/core/whatsapp.py` | `TwilioProvider`, `DummyProvider`, `get_whatsapp_provider()` |
| `apps/core/webhooks.py` | `WhatsAppWebhook`, `WhatsAppStatusCallback` |
| `apps/core/notifier.py` | `NotificationService`: patient email/WhatsApp notifications |
| `apps/core/services.py` | `CoreService`: newsletter, welcome email |
| `apps/authentication/adapters.py` | `SocialAccountAdapter`: Google OAuth (forces patient role) |
| `apps/authentication/services.py` | `AuthService`: verification and recovery emails |
| `apps/billing/services.py` | `InvoiceService`: invoice creation, confirmation and email |
| `apps/billing/views.py` | Invoice and payment confirmation views |
| `apps/billing/models.py` | `Facturas`, `ProfessionalPaymentInfo` |
| `apps/scheduling/services.py` | `AppointmentService`: appointment notifications |
| `apps/core/utils.py` | `validate_file_upload()`: attached file validation |

---

## See also / Ver también

- [`despliegue.md`](deployment.md) — Environment variables and Docker deployment
- [`seguridad.md`](security.md) — Webhook HMAC, rate limiting, secure cookies
- [`chatbot-ai.md`](chatbot-ai.md) — Gemini chatbot details
- [`roles-y-permisos.md`](roles-and-permissions.md) — Permissions per integration endpoint
- [`pagos-facturacion.md`](pagos-facturacion.md) — Billing and manual payment flow
- [`api.md`](api.md) — Complete REST endpoints reference
- [`pagos-facturacion.md`](pagos-facturacion.md) — Flujo de facturación y pagos manuales
- [`api.md`](api.md) — Referencia completa de endpoints REST
