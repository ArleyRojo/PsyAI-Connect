# Chatbot con Google Gemini — PsyAI Connect

> **Resumen:** Detalla la integración del chatbot de triaje psicológico con la API de Google Gemini: arquitectura, flujo de mensajes, rotación de API keys, detección de riesgo emocional y alerta de emergencia.  
> **Audiencia:** Desarrolladores que mantienen o extienden el chatbot.  
> **Nota importante:** Este chatbot es una herramienta de **triaje y apoyo emocional**, **no sustituye** la atención psicológica profesional.

---

## 1. Arquitectura general

```
┌─────────────┐     POST /api/chatbot/enviar      ┌──────────────────┐
│  Frontend   │ ────────────────────────────────► │  Django View     │
│  chatbot.js │  { mensaje, history }             │  (authentication)│
└─────────────┘                                   └────────┬─────────┘
                                                            │
                                                            ▼
┌─────────────┐     Respuesta JSON                  ┌──────────────────┐
│  Frontend   │ ◄─────────────────────────────────── │  ChatbotService  │
│  chatbot.js │  { respuesta, nivel_riesgo, ... }    │  (services.py)   │
└─────────────┘                                   └────────┬─────────┘
                                                            │
                              ┌─────────────────────────────┼─────────────────────────────┐
                              ▼                             ▼                             ▼
                     ┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
                     │  Google Gemini  │           │  ChatbotConfig  │           │  BD (Historial) │
                     │  API (Gemini)   │           │  (prompt, tone, │           │  Conversaciones │
                     │  (rotación keys)│           │   risk_terms,   │           │  Chatbot)       │
                     └─────────────────┘           └─────────────────┘           └─────────────────┘
```

---

## 2. Flujo de un mensaje

### Frontend (`static/js/modules/patient/chatbot.js`)

```javascript
// 1. Usuario envía mensaje
async function enviarMensaje(mensaje) {
  // Añade burbuja "typing..." al chat
  // Guarda mensaje en variable para posible reintento
  window.__lastChatbotMessage = mensaje;

  // 2. POST a /api/chatbot/enviar con fetchConTimeout (8s)
  const res = await fetchConTimeout('/api/chatbot/enviar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ mensaje })
  }, 8000);

  // 3. Procesa respuesta
  const data = await res.json();
  // Quita "typing..."
  // Añade respuesta del bot al chat
  agregarMensajeBot(data.respuesta || data.message);
}
```

**Manejo de errores:** Si falla (red, timeout, 5xx), `showChatbotError()` muestra burbuja con botón **Reintentar** que re-ejecuta `enviarMensaje(mensaje_original)`.

### Backend (`apps/chatbot/views.py` → `ChatbotService`)

```python
# apps/chatbot/services.py
class ChatbotService:
    def __init__(self):
        self.config = self._load_config()  # Cache 5 min

    def process_message(self, user_id, mensaje, historial):
        # 1. Construye prompt con system_prompt + historial (ventana configurable)
        # 2. Llama a Gemini API con rotación de keys
        # 3. Parsea respuesta JSON del modelo
        # 4. Detecta nivel de riesgo (alto/medio/bajo)
        # 5. Guarda en ConversacionesChatbot
        # 6. Si riesgo alto → envía email alerta_riesgo.html
        return {
            "respuesta": "...",
            "nivel_riesgo": "bajo|medio|alto",
            "palabras_riesgo": [...],
            "success": True
        }
```

---

## 3. Rotación de API Keys de Gemini

**Configuración** (`.env`):
```bash
GEMINI_API_KEY=key_principal           # Obligatoria
GEMINI_API_KEYS=key1,key2,key3         # Opcional: lista separada por comas
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_THINKING_LEVEL=low
# Timeouts y reintentos (segundos)
GEMINI_REQUEST_TIMEOUT_CONNECT=3       # timeout de conexión por intento
GEMINI_REQUEST_TIMEOUT_READ=8          # timeout de lectura por intento (intento 1)
GEMINI_MIN_READ_TIMEOUT_SECONDS=3      # read timeout mínimo garantizado aunque quede poco deadline
GEMINI_RETRIES=2                       # reintentos por error de red/timeout (default 2)
GEMINI_RETRY_BASE_DELAY=0.2            # retraso base entre reintentos (segundos)
GEMINI_TOTAL_DEADLINE_SECONDS=10       # presupuesto total (incluye reintentos + modelo de respaldo)
GEMINI_FALLBACK_MODEL=gemma-4-26b-a4b-it  # modelo de respaldo si el principal falla
```

**Implementación** (`apps/chatbot/services.py`):
```python
class GeminiClient:
    def __init__(self):
        self.keys = self._load_keys()  # [GEMINI_API_KEY] + GEMINI_API_KEYS.split(',')
        self.current_index = 0

    def _get_next_key(self):
        key = self.keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.keys)
        return key

    async def generate(self, prompt, config):
        # Reintenta con siguiente key si falla por cuota (429) o error temporal
        for _ in range(len(self.keys)):
            key = self._get_next_key()
            try:
                return await self._call_gemini(key, prompt, config)
            except QuotaExceeded:
                continue
        raise AllKeysExhausted()
```

**Ventajas:**
- Distribuye cuota entre múltiples proyectos de Google AI Studio
- Failover automático si una key agota su cuota
- Configurable vía variables de entorno (sin cambios de código)

---

## 4. Timeouts, reintentos y objetivo de latencia

### Objetivo de latencia

| Métrica | Valor objetivo |
|---------|---------------|
| p50 (respuesta completa) | ≤ 2 s |
| Fallback local garantizado antes de | ~10 s |
| Timeout del frontend (`CHATBOT_TIMEOUT_MS`) | 30 s |

### Configuración de timeouts

El backend usa un enfoque **escalonado** por intento:

| Intento | Connect timeout | Read timeout | Notas |
|---------|----------------|--------------|-------|
| 1 | 3 s | 8 s | Intento principal con Gemini |
| 2+ (reintentos) | ≤ 2 s | 10 s | Reintento tras fallo de red/timeout |

Además:
- `GEMINI_TOTAL_DEADLINE_SECONDS` (default **10 s**) limita el presupuesto total. Si el tiempo restante es menor que `GEMINI_MIN_READ_TIMEOUT_SECONDS` (default **3 s**), no se intenta otra llamada y se va directamente al fallback local.
- `GEMINI_RETRIES` (default **2**) define cuántos reintentos se hacen ante `Timeout` o `ConnectionError` antes de considerar que Gemini no está disponible.
- `GEMINI_RETRY_BASE_DELAY` (default **0.2 s**) es el retraso entre reintentos.

### Qué se reintenta vs qué no

| Error | ¿Reintenta? | ¿Rota key? | ¿Usa fallback? |
|-------|-------------|------------|----------------|
| `Timeout` / `ConnectionError` | Sí (hasta `GEMINI_RETRIES`) | No | Sí, tras agotar reintentos |
| HTTP 429 (cuota) | Sí | Sí | Sí, tras agotar keys + fallback model |
| HTTP 500/502/503/504 | Sí | No | Sí |
| HTTP 400 / 401 / 403 | No | No | Sí (inmediato) |
| HTTP 404 (modelo no encontrado) | No | No | Sí (inmediato) |

El flujo de fallo es:
1. Intento 1 con read timeout 8 s → si falla por timeout, reintento 2 inmediato con read timeout 10 s.
2. Si `GEMINI_RETRIES` se agota → prueba modelo de respaldo (`GEMINI_FALLBACK_MODEL`) si está configurado y difiere del principal.
3. Si todo falla → `build_response` entrega el **fallback local** (`_build_local_fallback`) con `success: True` y `fallback: True`, sin que el usuario quede esperando.

### Parámetros de configuración reducidos para menor latencia

- `max_tokens`: 600 → **300** (respuestas cortas de orientación, máximo 3-4 oraciones en el system prompt)
- `max_tokens_user`: 1000 → **800**
- `gemini_history_window`: 12 → **6** (menos tokens de entrada = menos tiempo de generación)
- `thinking_level`: se mantiene en `minimal` (mapa de `low` → `minimal`) para riesgo bajo; `medium` solo en riesgo medio/bajo.

---

## 5. Detección de riesgo emocional

### Configuración (`ChatbotConfig` - tabla `ChatbotConfig`)

| Campo | Descripción |
|-------|-------------|
| `risk_terms` | Palabras/frases que indican riesgo **alto** (ej: "suicidio", "matarme", "no quiero vivir") |
| `crisis_response` | Respuesta fija para riesgo alto (incluye teléfono de emergencia) |
| `medium_terms` | Palabras de riesgo **medio** (ej: "depresión", "ansiedad severa", "autolesión") |
| `medium_response` | Respuesta para riesgo medio (derivación a profesional) |
| `fallback_response` | Respuesta genérica si no hay match |
| `crisis_phone` | Teléfono de emergencia (default "106" - Colombia) |

### Detección en `ChatbotService._detect_risk()`

```python
def _detect_risk(self, mensaje, respuesta_modelo):
    mensaje_lower = mensaje.lower()

    # 1. Busca términos de alto riesgo (configurables)
    for term in self.config.risk_terms.split(','):
        if term.strip().lower() in mensaje_lower:
            return "alto", [term.strip()]

    # 2. Busca términos de riesgo medio
    detected_medium = []
    for term in self.config.medium_terms.split(','):
        if term.strip().lower() in mensaje_lower:
            detected_medium.append(term.strip())
    if detected_medium:
        return "medio", detected_medium

    # 3. Análisis de la respuesta del modelo (si incluye marcadores)
    if "RIESGO_ALTO" in respuesta_modelo:
        return "alto", []
    if "RIESGO_MEDIO" in respuesta_modelo:
        return "medio", []

    return "bajo", []
```

### Respuestas por nivel

| Nivel | Acción | Respuesta al usuario |
|-------|--------|---------------------|
| **Alto** | 1. Guarda `nivelEmocionalDetectado="alto"`<br>2. Envía email `alerta_riesgo.html` al profesional/admin<br>3. Respuesta incluye `crisis_phone` y derivación inmediata | `crisis_response` configurada (ej: "Parece que estás en una situación difícil. Por favor contacta ya al 106 o a tu profesional...") |
| **Medio** | 1. Guarda `nivelEmocionalDetectado="medio"`<br>2. Respuesta sugiere contactar profesional | `medium_response` configurada |
| **Bajo** | Respuesta normal del modelo | Respuesta del modelo Gemini |

---

## 5. Alerta de emergencia — `templates/emails/alerta_riesgo.html`

Se envía **solo en riesgo alto** (asunto: "⚠️ Alerta de riesgo — PsyAI Connect").

**Destinatarios:**
- Profesional asignado al paciente (si existe en `PacientesProfesional`)
- Admin (configurable)

**Contenido clave:**
- Nombre del paciente
- Fecha/hora de la conversación
- Fragmento del mensaje que disparó la alerta
- Nivel de riesgo detectado
- Teléfono de crisis (`crisis_phone`)
- Enlace directo a la conversación en el panel profesional

**Envío:** `MailService.send_recovery_email()` reutilizado con template `alerta_riesgo.html`.

---

## 6. Historial y configuración

### Historial (`ConversacionesChatbot`)

| Campo | Descripción |
|-------|-------------|
| `idConversacion` | PK |
| `idPaciente` | FK → `Register` |
| `mensajeUsuario` | Texto del usuario |
| `respuestaChatbot` | Respuesta del modelo |
| `nivelEmocionalDetectado` | `alto/medio/bajo` |
| `palabrasRiesgoDetectadas` | JSON/texto de términos hallados |
| `fecha` | Timestamp |

**Límite diario:** `daily_message_limit` (default 20) en `ChatbotConfig`. Al alcanzarlo, el bot responde mensaje de límite y bloquea formulario.

### Configuración dinámica (`ChatbotConfig`)

Un solo registro (singleton) editable desde panel admin (`/admin/chatbot/config/`). Cambios se propagan vía:
- `BroadcastChannel('chatbot-config')` (pestañas abiertas)
- EventSource SSE `/api/chatbot/config/events` (tiempo real)
- `window.focus` → recarga config

**Parámetros clave:**
| Campo | Default | Descripción |
|-------|---------|-------------|
| `system_prompt` | — | Prompt de sistema completo |
| `temperature` | 0.55 | Creatividad |
| `max_tokens` | 300 | Límite respuesta |
| `daily_message_limit` | 20 | Límite diario por usuario |
| `thinking_level` | `low` | `low/medium/high` (Gemini 2.5) |
| `prompt_history_window` | 4 | Mensajes previos en contexto |
| `crisis_phone` | `106` | Teléfono emergencia |

---

## 7. Frontend — `static/js/modules/patient/chatbot.js`

### Funciones clave

| Función | Descripción |
|---------|-------------|
| `enviarMensaje(mensaje)` | Flujo principal (ver §2) |
| `agregarMensajeUsuario/Bot()` | Añade a `historialChat` + `renderizarMensajes()` |
| `renderizarMensajes()` | Pinta burbujas con avatar, timestamp, agrupación |
| `mostrarSaludoInicial()` | Primer mensaje si no hay historial |
| `configurarFormulario()` | Submit → `enviarMensaje` |
| `configurarWelcomeChips()` | Chips de inicio rápidos (Ansiedad, Tristeza, etc.) |
| `configurarFullscreen()` | Modal pantalla completa |
| `configurarScrollToBottom()` | Botón "bajar" al final |
| `limpiarChat()` | Borra historial local + remoto (`DELETE /api/chatbot/historial`) |

### Estado
- `historialChat[]` — array en memoria + `localStorage` (clave `chatbotHistorial:<userId>`)
- `chatStorageKey` — carga remota al iniciar (`GET /api/chatbot/historial`)

---

## Ver también

- [`modelos-de-datos.md`](modelos-de-datos.md#7-appschatbot--chatbot-ia-y-chat-directo) — Modelos `ConversacionesChatbot`, `ChatbotConfig`, `MensajesChat`
- [`frontend.md`](frontend.md#7-archivos-js-principales-por-página) — Scripts del chatbot
- [`seguridad.md`](seguridad.md) — Rate limiting, validación de entrada
- [`roles-y-permisos.md`](roles-y-permisos.md) — Chatbot solo para pacientes
- [`despliegue.md`](despliegue.md) — Variables de entorno `GEMINI_API_KEY*`

---

## 9. Prediagnóstico al finalizar sesión

Al terminar una sesión en el chatbot, el paciente puede solicitar un **prediagnóstico orientativo** que resume la conversación y genera recomendaciones. El resultado se muestra al paciente en un modal y se notifica al profesional asignado.

> ⚠️ Es un apoyo orientativo generado por IA — **no un diagnóstico clínico**.

### 9.1 Flujo completo

```
Paciente pulsa "Finalizar sesión"
        │
        ▼
configurarFinalizarSesion()  [chatbot.js]
        │  POST /api/chatbot/prediagnostico/
        ▼
PrediagnosticoChatbotViewSet.create()  [chatbot/views.py]
        │
        ▼
ChatbotService.generar_prediagnostico(patient_id)  [chatbot/services.py]
        │
        ├─ chat_repo.get_history(today_only=True)  → historial del día
        │
        ├─ Override de seguridad: si algún mensaje tiene nivelEmocionalDetectado
        │  en {alto, critico} → fuerza requiere_atencion_urgente=True y
        │  escala nivel_riesgo a "alto" (sin depender del modelo)
        │
        ├─ _call_gemini_json(PREDIAGNOSTICO_SYSTEM_PROMPT, conversacion_texto)
        │  → JSON: resumen_paciente, resumen_profesional, posibles_areas,
        │           recomendaciones_paciente, nivel_riesgo, requiere_atencion_urgente
        │
        ├─ chat_repo.save_prediagnostico()  → BD: PrediagnosticoChatbot
        │
        └─ _notify_prediagnostico()
                ├─ appointment_repo.create_notification() (in-app para cada profesional)
                ├─ Si urgente → _send_risk_email()  [emails/alerta_riesgo.html]
                └─ Si no urgente → _send_prediagnostico_email()  [emails/prediagnostico.html]
        │
        ▼
Response 201 → {success, resumen, recomendaciones, nivel_riesgo}
        │
        ▼
Modal #prediagnosticoModal  [chatbot.html]
(muestra resumen_paciente + recomendaciones — nunca nivel_riesgo crudo)
```

### 9.2 Endpoint

| Método | URL | Permiso | Descripción |
|--------|-----|---------|-------------|
| `POST` | `/api/chatbot/prediagnostico/` | `IsAuthenticatedDRF` + `IsPaciente` | Genera y persiste el prediagnóstico de la sesión del día |
| `GET`  | `/api/prediagnosticos/profesional` | `IsAuthenticatedDRF` + `IsProfesional` | Lista los prediagnósticos de los pacientes asignados (últimos 30 días) |

### 9.3 Prompt de síntesis (`PREDIAGNOSTICO_SYSTEM_PROMPT`)

Definido en `services.py` (constante global). Instruye al modelo a responder **únicamente con JSON** con la estructura:

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

### 9.4 Override de seguridad

Antes de persistir el resultado del modelo, el servicio verifica si algún mensaje del historial tiene `nivelEmocionalDetectado` en `{alto, critico}`:

```python
if tiene_riesgo_alto_en_historial:
    resultado["requiere_atencion_urgente"] = True
    if resultado["nivel_riesgo"] not in {"alto", "critico"}:
        resultado["nivel_riesgo"] = "alto"
```

Esto garantiza que el sistema no subestime el riesgo aunque el modelo genere una respuesta conservadora.

### 9.5 Vistas

**Paciente:** modal `#prediagnosticoModal` en `chatbot.html`. Solo muestra `resumenPaciente` + `recomendaciones`. Nunca expone `nivel_riesgo` crudo ni el resumen clínico.

**Profesional:** pestaña "Prediagnósticos" en `patients.html`, cargada por `patients.prediagnostico.js`. Muestra `resumenProfesional`, áreas detectadas, nivel de riesgo con badge de color y badge "Urgente" cuando aplica.