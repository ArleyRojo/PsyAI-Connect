# Chatbot con Google Gemini — PsyAI Connect

> **Resumen:** Detalla la integración del chatbot de triaje psicológico con la API de Google Gemini: arquitectura, flujo de mensajes, rotación de API keys, detección de riesgo emocional y alerta de emergencia.  
> **Audiencia:** Desarrolladores que mantienen o extienden el chatbot.  
> **Nota importante:** Este chatbot es una herramienta de **triaje y apoyo emocional**, **no sustituye** la atención psicológica profesional.

---

## 1. Alcance del módulo

El módulo `apps/chatbot/` ofrece:

| Función | Descripción |
|---------|-------------|
| Mensajería | `POST /api/chatbot/enviar` — paciente envía mensaje, recibe respuesta del bot |
| Historial | `GET /api/chatbot` y `DELETE /api/chatbot/historial` — consultar y borrar historial |
| Configuración | `GET /api/chatbot/config` — leer configuración; SSE `/api/chatbot/config/events` para actualizaciones en tiempo real |
| Prediagnóstico | `POST /api/chatbot/prediagnostico` — resumen orientativo de la sesión del día |
| Encuesta | `POST /api/chatbot/encuesta` — utilidad, claridad, recomendación |
| Consentimiento | `GET/POST /paciente/consentimiento-chatbot` — opt-in/opt-out del paciente |
| Chat directo | `GET/POST /chat/mensajes`, `GET /chat/contactos`, `DELETE /chat/historial` — mensajería paciente–profesional |

Todas las vistas requieren autenticación (`IsAuthenticatedDRF`) y, para acciones de chatbot, el rol `IsPaciente`.

---

## 2. Arquitectura general

```
Paciente (frontend chatbot.js)
        │ POST /api/chatbot/enviar  { mensaje }
        ▼
Django View  (ChatbotViewSet.create, apps/chatbot/views.py)
        │ chatbot_service.build_response(patient_id, mensaje)
        ▼
ChatbotService  (apps/chatbot/services.py)
        ├─ 1. Límite diario (daily_message_limit)
        ├─ 2. Detección de riesgo (términos alto/medio/bajo)
        ├─ 3. Si riesgo alto/medio → respuesta fija de seguridad + notificación
        ├─ 4. Si riesgo bajo/sin riesgo → llama a Gemini (rotación de keys)
        ├─ 5. Fallback local si Gemini no está disponible
        └─ 6. Guarda en ConversacionesChatbot y devuelve JSON
```

## 3. Flujo de un mensaje

### 3.1 Frontend

El frontend vive en `templates/patient/aside-patient/chatbot.html` y usa `static/js/modules/patient/chatbot.js` (referenciado desde `templates/base/partials/scripts.html`).

Flujo principal (`enviarMensaje`):

1. Añade burbuja "escribiendo..." y guarda el mensaje para posible reintento.
2. Ejecuta `POST /api/chatbot/enviar` con `fetchConTimeout` (timeout 8 s, credenciales incluidas).
3. Procesa la respuesta JSON: quita el indicador de escritura y pinta la respuesta del bot con `agregarMensajeBot`.
4. Si falla (red, timeout, 5xx), `showChatbotError()` muestra un botón **Reintentar** que re-ejecuta `enviarMensaje` con el mensaje original.

### 3.2 Backend

`ChatbotService.build_response(patient_id, message)` en `apps/chatbot/services.py`:

| Paso | Acción |
|------|--------|
| 1 | Valida que el mensaje no esté vacío |
| 2 | Lee configuración desde `ChatbotConfig` (caché 30 s) |
| 3 | Verifica límite diario de mensajes del paciente |
| 4 | Detecta nivel de riesgo por términos configurados (alto / medio / bajo) |
| 5 | Riesgo alto → respuesta de crisis, notificación al profesional, guarda y retorna |
| 6 | Riesgo medio → respuesta de derivación, notificación, guarda y retorna |
| 7 | Riesgo bajo / sin riesgo → construye prompt y llama a Gemini |
| 8 | Gemini falla → `_build_local_fallback()` con respuesta empática predeterminada |
| 9 | Guarda conversación en `ConversacionesChatbot` y retorna JSON al frontend |

Respuesta típica del endpoint:

```json
{
  "success": true,
  "respuesta": "Texto de la respuesta del bot",
  "nivel_riesgo": "bajo",
  "palabras_riesgo": [],
  "used": 3,
  "limit": 20,
  "fallback": false
}
```

---

## 4. Rotación de API Keys de Gemini

El servicio lee las keys desde variables de entorno:

| Variable | Descripción | Obligatoria |
|----------|-------------|-------------|
| `GEMINI_API_KEY` | Key principal | Sí |
| `GEMINI_API_KEYS` | Keys adicionales separadas por coma | No |
| `GEMINI_MODEL` | Modelo principal (default `gemini-3.5-flash-lite`) | No |
| `GEMINI_FALLBACK_MODEL` | Modelo de respaldo (default `gemma-4-26b-a4b-it`) | No |
| `GEMINI_THINKING_LEVEL` | Nivel de razonamiento (`low/medium/high/none`) | No |

**Lógica de rotación** (`_call_gemini_with_rotation`):

1. Itera sobre las keys disponibles.
2. Si una key retorna `429` (cuota agotada) y hay más keys, rota a la siguiente.
3. Si se agotan todas las keys, prueba el modelo de respaldo (`GEMINI_FALLBACK_MODEL`) si difiere del principal.
4. Si todo falla, se activa el fallback local.

---

## 5. Timeouts, reintentos y objetivo de latencia

| Métrica | Valor objetivo |
|---------|---------------|
| p50 respuesta completa | ≤ 2 s |
| Presupuesto total backend | ≤ 10 s (`GEMINI_TOTAL_DEADLINE_SECONDS`) |
| Timeout frontend | 30 s |

Configuración de timeouts (variables de entorno):

| Variable | Default | Uso |
|----------|---------|-----|
| `GEMINI_REQUEST_TIMEOUT_CONNECT` | 3 s | Timeout de conexión por intento |
| `GEMINI_REQUEST_TIMEOUT_READ` | 8 s | Timeout de lectura intento 1 |
| `GEMINI_MIN_READ_TIMEOUT_SECONDS` | 3 s | Read timeout mínimo garantizado |
| `GEMINI_RETRIES` | 2 | Reintentos ante error de red/timeout |
| `GEMINI_RETRY_BASE_DELAY` | 0.2 s | Retraso base entre reintentos |

**Reintentos por tipo de error:**

| Error | Reintenta | Rota key | Fallback |
|-------|-----------|----------|----------|
| Timeout / ConnectionError | Sí | No | Sí |
| HTTP 429 (cuota) | Sí | Sí | Sí |
| HTTP 500/502/503/504 | Sí | No | Sí |
| HTTP 400 / 401 / 403 / 404 | No | No | Sí (inmediato) |

Si se agotan reintentos, key y fallback, se entrega `_build_local_fallback()` con `success: true` y `fallback: true` para que el usuario nunca quede esperando.

---

## 6. Detección de riesgo emocional

La detección se basa en `ChatbotConfig` (tabla `ChatbotConfig`), editable desde el panel de administración.

| Campo | Descripción |
|-------|-------------|
| `risk_terms` | JSON con palabras y nivel (`Alto`, `Medio`, `Bajo`) |
| `crisis_response` | Respuesta fija para riesgo alto |
| `medium_terms` | Términos de riesgo medio |
| `medium_response` | Respuesta para riesgo medio |
| `fallback_response` | Respuesta genérica por defecto |
| `crisis_phone` | Teléfono de emergencia (default `106`, Colombia) |

**Lógica en `_detect_risk` / `build_response`:**

1. Busca términos de riesgo **alto** en el mensaje del usuario → nivel `Alto`, respuesta de crisis, notificación urgente.
2. Busca términos de riesgo **medio** → nivel `Medio`, respuesta de derivación, notificación.
3. Si hay términos **bajo** → nivel `Bajo`, continúa a Gemini con contexto de bajo riesgo.
4. Si no hay match → `Sin riesgo`, llama a Gemini normalmente.

**Notificaciones de riesgo:**

- Riesgo alto/medio: crea notificación in-app para el profesional asignado (o todos los profesionales si no hay asignado) y envía email con plantilla `templates/emails/alerta_riesgo.html`.
- Evita notificaciones duplicadas en un ventana de 12 horas (`_ya_notificado_recientemente`).

---

## 7. Prediagnóstico orientativo

Endpoint: `POST /api/chatbot/prediagnostico` (rol paciente). Implementado en `PrediagnosticoChatbotViewSet.create` → `ChatbotService.generar_prediagnostico`.

**Flujo:**

1. Obtiene el historial del día del paciente (`chat_repo.get_history(today_only=True)`).
2. Override de seguridad: si algún mensaje del día tiene nivel `alto` o `critico`, fuerza `requiere_atencion_urgente=true` y escala el nivel a `alto`, independientemente de lo que diga el modelo.
3. Llama a Gemini con `PREDIAGNOSTICO_SYSTEM_PROMPT` (constante en `services.py`) que obliga a responder solo JSON.
4. Guarda el resultado en `PrediagnosticoChatbot` (BD).
5. Notifica al profesional asignado: crea notificación in-app y envía email (`alerta_riesgo.html` si urgente, `prediagnostico.html` si no).

**Estructura JSON de respuesta del modelo:**

```json
{
  "resumen_paciente": "...",
  "resumen_profesional": "...",
  "posibles_areas": ["área 1", "área 2"],
  "recomendaciones_paciente": ["rec 1", "rec 2"],
  "nivel_riesgo": "bajo|moderado|alto|critico",
  "requiere_atencion_urgente": false
}
```

**Modelo BD:** `PrediagnosticoChatbot` con campos `resumenPaciente`, `resumenProfesional`, `posiblesAreas` (JSON), `recomendaciones` (JSON), `nivelRiesgo` (`bajo|moderado|alto|critico`), `requiereAtencionUrgente`, `profesionalNotificado`, `fecha`.

**Vista profesional:** `GET /api/prediagnosticos/profesional` lista los prediagnósticos de pacientes asignados (últimos 30 días).

> ⚠️ El prediagnóstico es orientativo generado por IA — **no un diagnóstico clínico**.

---

## 8. Configuración dinámica (`ChatbotConfig`)

Un registro singleton editable desde el panel admin (`/admin/chatbot/chatbotconfig/`). Campos principales:

| Campo | Default | Descripción |
|-------|---------|-------------|
| `system_prompt` | fallback interno | Prompt de sistema |
| `tone` | `empatico` | Tono de respuesta |
| `risk_terms` | `[]` | Términos de riesgo por nivel |
| `crisis_response` | texto default | Respuesta de crisis |
| `medium_response` | texto default | Respuesta riesgo medio |
| `fallback_response` | `¿Cómo te sientes hoy?` | Respuesta genérica |
| `off_topic_response` | texto default | Respuesta fuera de tema |
| `crisis_phone` | `106` | Teléfono emergencia |
| `thinking_level` | `low` | `low/medium/high/none` |
| `prompt_history_window` | 4 | Mensajes de historial en prompt |
| `gemini_history_window` | 12 | Ventana de historial para Gemini |
| `temperature` | 0.55 | Creatividad del modelo |
| `top_p` | 0.9 | Muestreo del modelo |
| `max_tokens` | 600 | Límite de tokens de respuesta |
| `max_tokens_user` | 1000 | Límite tokens usuario |
| `daily_message_limit` | 20 | Límite diario por paciente |

**Propagación de cambios:** al guardar la configuración, `ChatbotConfigService.save_config` publica el evento vía `ChatbotConfigEventsService` (cola en memoria) y los clientes lo reciben por SSE en `GET /api/chatbot/config/events` o por `BroadcastChannel('chatbot-config')` en pestañas abiertas.

**Caché:** `ChatbotService` cachea la configuración 30 segundos (`CONFIG_CACHE_TTL_SECONDS = 30`). Al guardar, se invalida en todas las instancias del servicio registradas.

---

## 9. Historial y modelos de datos

### `ConversacionesChatbot`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `idConversacion` | PK | Identificador |
| `idPaciente` | FK → `Register` | Paciente |
| `mensajeUsuario` | Text | Mensaje del usuario |
| `respuestaChatbot` | Text | Respuesta del bot |
| `nivelEmocionalDetectado` | Char | `Alto/Medio/Bajo/Sin riesgo` |
| `palabrasRiesgoDetectadas` | Text | Términos detectados |
| `fecha` | DateTime | Timestamp |

### `PrediagnosticoChatbot`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `idPrediagnostico` | PK | Identificador |
| `idPaciente` | FK → `Register` | Paciente |
| `resumenPaciente` | Text | Resumen para el paciente |
| `resumenProfesional` | Text | Resumen clínico orientativo |
| `posiblesAreas` | JSON | Áreas detectadas |
| `recomendaciones` | JSON | Recomendaciones |
| `nivelRiesgo` | Char | `bajo|moderado|alto|critico` |
| `requiereAtencionUrgente` | Boolean | Urgente |
| `profesionalNotificado` | Boolean | Notificado |
| `fecha` | DateTime | Timestamp |

### `ChatbotConfig`

Configuración singleton del chatbot (ver tabla en §8).

### `EncuestaChatbot`

Encuesta post-sesión: `utilidad` (bool), `claridad` (bool), `recomendaria` (`si/no`), `comentario` (texto).

### `MensajesChat`

Mensajería directa paciente–profesional: `idEmisor`, `idReceptor`, `mensaje`, `leido`, `fecha`.

---

## 10. Endpoints del módulo chatbot

| Método | Endpoint | Permiso | Descripción |
|--------|----------|---------|-------------|
| `POST` | `/api/chatbot/enviar` | Autenticado + Paciente | Enviar mensaje al chatbot |
| `GET` | `/api/chatbot` | Autenticado + Paciente | Obtener historial |
| `DELETE` | `/api/chatbot/historial` | Autenticado + Paciente | Borrar historial |
| `GET` | `/api/chatbot/config` | Autenticado + Paciente | Leer configuración |
| `GET` | `/api/chatbot/config/events` | Autenticado + Sesión | SSE de cambios de configuración |
| `POST` | `/api/chatbot/prediagnostico` | Autenticado + Paciente | Generar prediagnóstico |
| `GET` | `/api/prediagnosticos/profesional` | Autenticado + Profesional | Listar prediagnósticos asignados |
| `POST` | `/api/chatbot/encuesta` | Autenticado + Paciente | Enviar encuesta de satisfacción |
| `GET` | `/paciente/consentimiento-chatbot` | Autenticado + Paciente | Leer consentimiento |
| `POST` | `/paciente/consentimiento-chatbot` | Autenticado + Paciente | Actualizar consentimiento |
| `GET` | `/chat/contactos` | Autenticado + Paciente | Listar profesionales con mensajes |
| `GET` | `/chat/mensajes` | Autenticado | Obtener mensajes de una conversación |
| `POST` | `/chat/mensajes` | Autenticado | Enviar mensaje directo |
| `DELETE` | `/chat/historial` | Autenticado + Paciente | Borrar historial de chat |

---

## 11. Variables de entorno relevantes

Definidas en `.env` y documentadas en [`despliegue.md`](despliegue.md#8-variables-de-entorno-env):

- `GEMINI_API_KEY`, `GEMINI_API_KEYS`, `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`
- `GEMINI_THINKING_LEVEL`, `GEMINI_REQUEST_TIMEOUT_CONNECT`, `GEMINI_REQUEST_TIMEOUT_READ`
- `GEMINI_MIN_READ_TIMEOUT_SECONDS`, `GEMINI_RETRIES`, `GEMINI_RETRY_BASE_DELAY`
- `GEMINI_TOTAL_DEADLINE_SECONDS`
- `SITE_URL` (usado en enlaces de email de alerta)

---

## 12. Archivos clave

| Ruta | Contenido |
|------|-----------|
| `apps/chatbot/services.py` | `ChatbotService`, `ChatbotConfigService`, detección de riesgo, llamada a Gemini, fallback, prediagnóstico, notificaciones |
| `apps/chatbot/views.py` | ViewSets: `ChatbotViewSet`, `PrediagnosticoChatbotViewSet`, `ChatbotConfigViewSet`, `ChatbotConfigEventsResource`, `ChatMensajeViewSet`, `ConsentimientoChatbotViewSet`, etc. |
| `apps/chatbot/models.py` | `ConversacionesChatbot`, `PrediagnosticoChatbot`, `ChatbotConfig`, `EncuestaChatbot`, `MensajesChat` |
| `apps/chatbot/urls.py` | Definición de todos los endpoints del módulo |
| `apps/chatbot/repositories.py` | Capa de acceso a datos (`ChatRepository`, `ChatbotConfigRepository`, `MensajesRepository`) |
| `templates/patient/aside-patient/chatbot.html` | Vista del paciente (chat) |
| `templates/admin/aside-admin/chatbot.config.html` | Panel de configuración del admin |
| `templates/emails/alerta_riesgo.html` | Plantilla de email de alerta de riesgo |

---

## 13. Ver también

- [`despliegue.md`](deployment.md) — Variables de entorno `GEMINI_API_KEY*` y despliegue con Docker
- [`modelos-de-datos.md`](data-models.md) — Modelos del chatbot y relaciones
- [`frontend.md`](frontend.md) — Scripts JS del chatbot y organización de `static/js/`
- [`roles-y-permisos.md`](roles-and-permissions.md) — `IsPaciente`, permisos del chatbot
- [`seguridad.md`](security.md) — Rate limiting y validación de entrada
- [`api.md`](api.md) — Referencia completa de endpoints REST
- [`architecture.md`](architecture.md) — Arquitectura general del sistema