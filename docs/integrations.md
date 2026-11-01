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
- [`api.md`](api.md) — Referencia completa de endpoints REST