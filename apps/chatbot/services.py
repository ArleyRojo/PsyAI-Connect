import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from queue import Queue
from threading import Lock

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.chatbot.repositories import (
    ChatRepository,
    ChatbotConfigRepository,
    MensajesRepository,
)
from apps.scheduling.repositories import AppointmentRepository

GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
GEMINI_RETRIES = 2
GEMINI_RETRY_BASE_DELAY = 0.6
SYSTEM_PROMPT_FALLBACK = "Actua como un asistente de triaje psicologico para PsyAI Connect."
CONFIG_CACHE_TTL_SECONDS = 30

_PROMPT_SUFFIX = """

ALCANCE TEMÁTICO — LÍMITES ESTRICTOS:

Tu único propósito es acompañar al usuario en temas de bienestar emocional,
salud mental y orientación psicológica básica. NO eres un asistente general.

PUEDES responder sobre:
- Emociones, estados de ánimo, estrés, ansiedad, tristeza, relaciones
  personales, autoestima, hábitos de sueño, manejo de conflictos,
  motivación, duelo, y temas afines al bienestar psicológico.
- Preguntas sobre cómo funciona la plataforma, cómo agendar cita con un
  profesional, o cómo usar el chatbot.
- Charla breve y cálida de cortesía (saludos, cómo está el usuario), siempre
  que sirva para abrir o mantener la conversación emocional, no como fin en
  sí misma.

NO PUEDES responder, ni aunque el usuario insista, sobre:
- Tareas académicas, programación, matemáticas, cultura general, deportes,
  noticias, entretenimiento, recetas, traducción de textos, o cualquier
  tema sin relación con salud emocional/mental.
- Diagnósticos médicos generales no psicológicos (ej. "me duele la cabeza,
  ¿qué tomo?", síntomas físicos): redirige siempre a un médico general,
  no dentro de tu alcance.
- Escribir código, ensayos, resúmenes de libros, contenido creativo sin
  relación con el bienestar del usuario, o cualquier tarea que use al
  chatbot como herramienta general de productividad.
- Opiniones sobre política, religión, temas legales, financieros o
  cualquier consejo fuera del ámbito psicológico.

CÓMO RESPONDER A UN TEMA FUERA DE ALCANCE:
1. No expliques ni resuelvas el tema pedido, ni parcialmente.
2. Redirige con calidez en 1-2 frases, sin sonar como un mensaje de error
   automático. Ejemplos de tono (no los repitas literal, varía la redacción):
   - "Esa no es un área en la que pueda ayudarte, pero cuéntame, ¿cómo te
     has sentido últimamente?"
   - "Eso se sale un poco de lo que puedo acompañarte aquí. Si quieres,
     hablemos de cómo has estado emocionalmente."
 3. Si el usuario insiste varias veces seguidas en el mismo tema fuera de
    alcance, mantén el límite con la misma calidez, sin ceder ni explicar el
    tema "solo un poco". No niegues cortésmente y luego respondas parcialmente.
 4. Nunca digas "no tengo permitido" ni expliques que sigues una regla
    interna — simplemente redirige de forma natural, como lo haría una
    persona que no maneja ese tema.

OPCIÓN DETERMINISTA — ETIQUETA DE SALIDA:
- Cuando el tema esté CLARAMENTE fuera de alcance (sin relación alguna con
  bienestar emocional, salud mental u orientación psicológica) y no exista
  un ángulo emocional al cual redirigirlo de forma natural, responde
  EXACTAMENTE con esta etiqueta y nada más (sin texto adicional):

  [FUERA_DE_TEMA]

- Usa la etiqueta únicamente en casos inequívocos. Si existe alguna conexión
  emocional posible (aunque sea remota), prefiere siempre la redirección
  cálida de los puntos anteriores en lugar de la etiqueta. La etiqueta NO se
  usa cuando hay indicios de riesgo emocional: ahí siempre responde con la
  respuesta de riesgo correspondiente.

CASOS AMBIGUOS (síntomas físicos con causa emocional):
- Si el usuario menciona síntomas físicos que suelen tener origen emocional
  (insomnio, fatiga, tensión muscular, pérdida de apetito ligada a ansiedad
  o tristeza), SÍ puedes explorarlos como parte del acompañamiento
  emocional, pero deja claro que para lo físico debe consultar a un médico.

COMPORTAMIENTO OBLIGATORIO:
- Responde en texto plano, sin listas, viñetas ni encabezados.
- Máximo 3 oraciones por respuesta.
- Una sola pregunta por respuesta, nunca dos seguidas.
- Valida primero el sentimiento antes de cualquier pregunta o consejo.
- Varía cómo comienzas cada mensaje, nunca repitas la misma apertura.
- Nunca uses "Entiendo perfectamente", "Claro que sí", "Por supuesto" ni exclamaciones en exceso.
- Usa el mismo registro del paciente: informal si escribe informal, formal si escribe formal.

EJEMPLOS DE CÓMO RESPONDER:

Usuario: "me siento solo"
MAL: "Entiendo que te sientes solo. La soledad puede ser difícil. ¿Tienes amigos o familiares con quienes hablar?"
BIEN: "Eso pesa mucho. ¿Hace cuánto estás sintiendo eso?"

Usuario: "tuve un día horrible"
MAL: "Lamento escuchar eso. Los días malos son difíciles. ¿Qué pasó hoy?"
BIEN: "Qué día tan duro. ¿Qué fue lo más que te afectó?"

Usuario: "no sé si puedo más"
MAL: "Entiendo que estás pasando por un momento difícil. Es importante buscar ayuda profesional."
BIEN: "Suena a que estás cargando mucho. ¿Qué es lo que más te está pesando ahorita?"

COHERENCIA CONVERSACIONAL — OBLIGATORIO:

Tienes acceso al historial reciente de esta conversación (los últimos
mensajes intercambiados). Úsalo siempre antes de responder. Reglas:

1. NO vuelvas a preguntar algo que el usuario ya te contó en mensajes
   anteriores de esta misma conversación (su nombre, motivo de consulta,
   situación que describió, cómo se sentía, etc.). Si necesitas retomarlo,
   haz referencia a ello en vez de preguntarlo de nuevo.
   Mal ejemplo: usuario ya dijo "me peleé con mi pareja" → bot pregunta
   luego "¿qué te trae por aquí hoy?" (ignora lo ya dicho).
   Bien: "Volviendo a lo de la pelea con tu pareja, ¿cómo te sientes ahora?"

2. NO te contradigas de un mensaje a otro. Si en un mensaje sugeriste algo
   (ej. "podría ayudarte escribir lo que sientes"), no des una indicación
   opuesta más adelante sin explicar por qué cambia tu recomendación.

3. Mantén el mismo tono y nivel de formalidad a lo largo de TODA la
   conversación (definido por la configuración de tono del sistema). No
   cambies de repente a un registro más formal o más informal sin razón.

4. Si el usuario cambia de tema abruptamente, puedes seguirlo, pero si el
   nuevo tema sigue relacionado con lo emocional, intenta conectar
   brevemente con lo anterior si tiene sentido (sin forzarlo si de verdad
   son cosas distintas).

5. Antes de responder, ubica mentalmente en qué punto va la conversación:
   ¿es el primer mensaje?, ¿ya se habló del motivo de consulta?, ¿ya
   ofreciste una sugerencia que el usuario no ha comentado si le sirvió?
   Actúa en consecuencia, no como si cada mensaje fuera aislado.

6. No repitas la misma sugerencia, frase de apertura o estructura de
   respuesta dos veces seguidas en la conversación. Varía la redacción,
   pero mantén la misma línea de acompañamiento.

7. Si el usuario responde algo breve tipo "sí", "no", "no sé", interpreta
   la respuesta en el contexto de tu pregunta anterior — nunca trates un
   "sí"/"no" como si fuera un mensaje nuevo sin contexto.

8. Si en algún punto detectas que ya no tienes claridad sobre algo que el
   usuario mencionó antes (por ejemplo, si el historial disponible es muy
   corto y no alcanza a ver todo el contexto), es preferible preguntar con
   naturalidad ("recuérdame, ¿qué me dijiste que...") a asumir o inventar.
"""


class ChatbotConfigEventsService:
    def __init__(self):
        self._subscribers = []
        self._subscribers_lock = Lock()

    def subscribe(self):
        q = Queue()
        with self._subscribers_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q):
        with self._subscribers_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def publish_config_update(self, config):
        event = json.dumps(config or {})
        with self._subscribers_lock:
            subscribers = list(self._subscribers)
        for q in subscribers:
            q.put(event)


chatbot_config_events = ChatbotConfigEventsService()
subscribe_config = chatbot_config_events.subscribe
unsubscribe_config = chatbot_config_events.unsubscribe
publish_config_update = chatbot_config_events.publish_config_update


class ChatEventsService:
    def __init__(self):
        self._subscribers = {}
        self._subscribers_lock = Lock()

    def subscribe(self, user_id):
        q = Queue()
        user_id = int(user_id)
        with self._subscribers_lock:
            self._subscribers.setdefault(user_id, []).append(q)
        return q

    def unsubscribe(self, user_id, q):
        user_id = int(user_id)
        with self._subscribers_lock:
            queues = self._subscribers.get(user_id, [])
            if q in queues:
                queues.remove(q)
            if not queues and user_id in self._subscribers:
                del self._subscribers[user_id]

    def publish_message(self, id_mensaje, id_emisor, id_receptor):
        event = json.dumps({
            "idMensaje": id_mensaje,
            "idEmisor": id_emisor,
            "idReceptor": id_receptor,
        })
        recipients = {int(id_emisor), int(id_receptor)}
        with self._subscribers_lock:
            subscribers = [
                q
                for uid in recipients
                for q in self._subscribers.get(uid, [])
            ]
        for q in subscribers:
            q.put(event)


chat_events = ChatEventsService()
subscribe_chat = chat_events.subscribe
unsubscribe_chat = chat_events.unsubscribe
publish_message = chat_events.publish_message

_chatbot_service_registry = []


class ChatbotConfigService:
    def __init__(self):
        self.repo = ChatbotConfigRepository()

    def get_config(self):
        config = self.repo.get_config()
        if not config:
            return {
                "success": True,
                "config": {
                    "system_prompt": "",
                    "tone": "",
                    "interaction_rules": "",
                    "risk_terms": "[]",
                    "crisis_response": "",
                 "medium_response": "",
                "fallback_response": "",
                "off_topic_response": "Ese tema se sale de mi alcance, pero si quieres cuéntame cómo te has sentido emocionalmente.",
                "crisis_phone": "106",
                    "thinking_level": "low",
                    "prompt_history_window": 4,
                    "gemini_history_window": 12,
                    "temperature": 0.55,
                    "top_p": 0.9,
                    "max_tokens": 600,
                    "max_tokens_user": 1000,
                    "daily_message_limit": 20,
                    "fecha_actualizacion": None,
                    "actualizado_por": None,
                },
            }, 200
        return {"success": True, "config": config}, 200

    def save_config(self, data, admin_id):
        error = self._validate_config(data)
        if error:
            return {"success": False, "message": error}, 400
        self.repo.save_config(data, admin_id)
        nueva_config = self.repo.get_config()
        publish_config_update(nueva_config)
        self._invalidate_chatbot_caches()
        return {"success": True, "message": "Configuración guardada correctamente"}, 200

    def save_risk_terms(self, risk_terms_str, admin_id):
        self.repo.save_risk_terms_only(risk_terms_str, admin_id)
        config = self.repo.get_config()
        publish_config_update(config)
        self._invalidate_chatbot_caches()
        return {"success": True, "message": "Términos de riesgo guardados"}, 200

    def clear_risk_terms(self, admin_id):
        self.repo.clear_risk_terms(admin_id)
        publish_config_update({"risk_terms": "[]"})
        self._invalidate_chatbot_caches()
        return {"success": True, "message": "Términos de riesgo eliminados"}, 200

    def _invalidate_chatbot_caches(self):
        for svc in list(_chatbot_service_registry):
            svc.invalidate_config_cache()

    def _validate_config(self, data):
        validators = {
            "temperature": (0.0, 1.0),
            "top_p": (0.0, 1.0),
            "max_tokens": (100, 1000),
            "max_tokens_user": (200, 1000),
            "daily_message_limit": (1, 200),
            "prompt_history_window": (1, 20),
            "gemini_history_window": (4, 50),
        }
        for field, (lo, hi) in validators.items():
            if field in data:
                try:
                    val = float(data[field])
                except (TypeError, ValueError):
                    return f"El campo {field} debe ser un número."
                if val < lo or val > hi:
                    return f"El campo {field} debe estar entre {lo} y {hi}."
        if "thinking_level" in data:
            allowed = {"low", "medium", "high", "none"}
            if data["thinking_level"] not in allowed:
                return f"thinking_level debe ser uno de: {', '.join(sorted(allowed))}"
        return None

    def get_historial_palabras_riesgo(self):
        rows = self.repo.get_historial_palabras_riesgo()
        aggregated = {}
        for row in rows:
            nombre = row.get("nombre", "")
            nivel = row.get("nivelEmocionalDetectado", "Bajo")
            palabras_raw = row.get("palabrasRiesgoDetectadas", "")
            if not palabras_raw:
                continue
            for palabra in palabras_raw.split(","):
                palabra = palabra.strip().lower()
                if not palabra:
                    continue
                key = (palabra, nivel)
                if key not in aggregated:
                    aggregated[key] = {"palabra": palabra, "nivel": nivel, "count": 0, "pacientes": set()}
                aggregated[key]["count"] += 1
                if nombre and nombre not in aggregated[key]["pacientes"]:
                    aggregated[key]["pacientes"].add(nombre)
        result = []
        for item in aggregated.values():
            item["pacientes"] = sorted(item["pacientes"])
            result.append(item)
        result.sort(key=lambda x: x["count"], reverse=True)
        return {"success": True, "palabras": result}, 200


class ChatEventsServiceManager:
    def __init__(self):
        self.repo = MensajesRepository()
        self.chat_repo = ChatRepository()

    def get_contactos_con_mensajes(self, id_usuario, lista_contactos, id_field="idUsuario"):
        try:
            from apps.core.telemetry import get_active_user_ids
            online_ids = set(get_active_user_ids())
        except ImportError:
            online_ids = set()

        id_otro_ids = [c.get(id_field) for c in lista_contactos if c.get(id_field)]
        ultimos = self.repo.get_ultimos_mensajes_batch(id_usuario, id_otro_ids)
        no_leidos = self.repo.contar_no_leidos_batch(id_usuario, id_otro_ids)

        resultado = []
        for contacto in lista_contactos:
            uid = contacto.get(id_field)
            ultimo = ultimos.get(uid)
            nl = no_leidos.get(str(uid), 0)
            resultado.append({
                **contacto,
                "ultimoMensaje": ultimo["mensaje"][:60] if ultimo else None,
                "ultimaFecha": str(ultimo["fecha"]) if ultimo else None,
                "ultimoIdMensaje": ultimo["idMensaje"] if ultimo else 0,
                "ultimoEmisor": ultimo["idEmisor"] if ultimo else None,
                "noLeidos": nl,
                "isOnline": uid in online_ids,
            })
        return sorted(
            resultado,
            key=lambda c: (
                1 if c.get("noLeidos", 0) else 0,
                c.get("ultimaFecha") or "",
                c.get("ultimoIdMensaje") or 0,
            ),
            reverse=True,
        )

    def get_mensajes(self, id_usuario, id_otro, desde_id=0):
        self.repo.marcar_leidos(id_usuario, id_otro)
        rows = self.repo.get_conversacion(id_usuario, id_otro, desde_id)
        return [
            {**row, "esMio": row["idEmisor"] == id_usuario, "fecha": str(row["fecha"])}
            for row in rows
        ]

    def enviar_mensaje(self, id_emisor, id_receptor, mensaje):
        return self.repo.enviar_mensaje(id_emisor, id_receptor, mensaje)

    def eliminar_historial_chatbot(self, patient_id):
        self.chat_repo.delete_history(patient_id)


class ChatbotService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.chat_repo = ChatRepository()
        self.appointment_repo = AppointmentRepository()
        self.config_repo = ChatbotConfigRepository()
        self._cached_config_version = None
        self._cached_config = None
        self._cached_system_prompt = None
        self._cached_config_ts = 0.0
        self._key_index = 0
        _chatbot_service_registry.append(self)

    def _now_ts(self):
        return datetime.now(timezone.utc).timestamp()

    def invalidate_config_cache(self):
        self._cached_config = None
        self._cached_config_version = None
        self._cached_config_ts = 0.0

    def _get_api_keys(self):
        multi = os.getenv("GEMINI_API_KEYS", "").strip()
        if multi:
            keys = [k.strip() for k in multi.split(",") if k.strip()]
            if keys:
                return keys
        single = os.getenv("GEMINI_API_KEY", "").strip()
        return [single] if single else []

    def _next_key(self, keys):
        if not keys:
            return None
        self._key_index = (self._key_index + 1) % len(keys)
        return keys[self._key_index]

    def _get_fallback_model(self):
        return os.getenv("GEMINI_FALLBACK_MODEL", "gemma-4-26b-a4b-it").strip()

    def _get_chatbot_config(self):
        now = self._now_ts()
        if self._cached_config is not None and now - self._cached_config_ts < CONFIG_CACHE_TTL_SECONDS:
            return self._cached_config, self._cached_config_version
        try:
            row = self.config_repo.get_config()
        except Exception:
            row = None
        version = None
        if row and isinstance(row, dict):
            version = row.get("fecha_actualizacion")
            if hasattr(version, "isoformat"):
                version = version.isoformat()
            version = str(version) if version is not None else None
        if version == self._cached_config_version and self._cached_config is not None:
            return self._cached_config, self._cached_config_version
        if row:
            result = dict(row)
        else:
            result = {
                "system_prompt": SYSTEM_PROMPT_FALLBACK,
                "risk_terms": "[]",
                "crisis_response": "Si hay riesgo, llama al 123.",
                "medium_response": "",
                "fallback_response": "¿Cómo te sientes hoy?",
                "off_topic_response": "Eso se sale un poco del lugar donde puedo acompañarte hoy. Cuéntame: ¿cómo te has sentido emocionalmente?",
                "crisis_phone": "106",
                "thinking_level": "low",
                "tone": None,
                "interaction_rules": None,
                "prompt_history_window": 4,
                "gemini_history_window": 12,
                "temperature": 0.55,
                "top_p": 0.9,
                "max_tokens": 600,
                "max_tokens_user": 1000,
                "daily_message_limit": 20,
            }
        result.setdefault("risk_terms", result.get("risk_terms") or "[]")
        result.setdefault("crisis_response", result.get("crisis_response") or "")
        result.setdefault("medium_response", result.get("medium_response") or "")
        result.setdefault("fallback_response", result.get("fallback_response") or "")
        result.setdefault("crisis_phone", result.get("crisis_phone") or "106")
        result.setdefault("thinking_level", result.get("thinking_level") or "low")
        result.setdefault("temperature", result.get("temperature", 0.55))
        result.setdefault("top_p", result.get("top_p", 0.9))
        result.setdefault("max_tokens", result.get("max_tokens", 600))
        result.setdefault("max_tokens_user", result.get("max_tokens_user", 1000))
        result.setdefault("prompt_history_window", result.get("prompt_history_window", 4))
        result.setdefault("gemini_history_window", result.get("gemini_history_window", 12))
        result.setdefault("daily_message_limit", result.get("daily_message_limit", 20))
        self._cached_config = result
        self._cached_config_version = version
        self._cached_config_ts = now
        return self._cached_config, self._cached_config_version

    def build_response(self, patient_id, message):
        message = (message or "").strip()
        if not message:
            return {"success": False, "message": "Mensaje requerido"}, 400

        config, _ = self._get_chatbot_config()
        daily_limit = int(config.get("daily_message_limit") or 20)
        crisis_phone = config.get("crisis_phone") or "106"
        used_today = self.chat_repo.count_today_messages(patient_id)
        if used_today >= daily_limit:
            return {
                "success": False,
                "limit_reached": True,
                "used": used_today,
                "limit": daily_limit,
                "message": (
                    f"Has alcanzado el límite de {daily_limit} mensajes por hoy. "
                    "Si estás en una situación de urgencia, contacta a tu profesional "
                    f"asignado o llama a la línea de crisis: {crisis_phone}."
                ),
            }, 429

        prompt_window = int(config.get("prompt_history_window") or 4)
        gemini_window = int(config.get("gemini_history_window") or 12)
        history = self.chat_repo.get_history(patient_id, today_only=False, limit=gemini_window)

        try:
            risk_list = json.loads(config.get("risk_terms") or "[]")
        except Exception:
            risk_list = []

        alto_terms = [self._normalize_text(r["palabra"].strip()) for r in risk_list if r.get("nivel") == "Alto" and r.get("palabra")]
        medio_terms = [self._normalize_text(r["palabra"].strip()) for r in risk_list if r.get("nivel") == "Medio" and r.get("palabra")]
        bajo_terms = [self._normalize_text(r["palabra"].strip()) for r in risk_list if r.get("nivel") == "Bajo" and r.get("palabra")]

        normalized = self._normalize_text(message)
        es_alto = any(re.search(rf"\b{re.escape(t)}\b", normalized) for t in alto_terms)
        es_medio = any(re.search(rf"\b{re.escape(t)}\b", normalized) for t in medio_terms)
        es_bajo = any(re.search(rf"\b{re.escape(t)}\b", normalized) for t in bajo_terms)

        if es_alto:
            nivel_emocional = "Alto"
            risk_words = ",".join([t for t in alto_terms if re.search(rf"\b{re.escape(t)}\b", normalized)])
            self._notify_high_risk(patient_id)
            self.chat_repo.save_conversation(
                patient_id, message, config.get("crisis_response", ""), nivel_emocional, risk_words
            )
            return {
                "success": True,
                "respuesta": config.get("crisis_response", ""),
                "risk_detected": True,
                "used": used_today + 1,
                "limit": daily_limit,
            }, 200

        if es_medio:
            nivel_emocional = "Medio"
            risk_words = ",".join([t for t in medio_terms if re.search(rf"\b{re.escape(t)}\b", normalized)])
            self._notify_medium_risk(patient_id, risk_words)
        elif es_bajo:
            nivel_emocional = "Bajo"
            risk_words = ",".join([t for t in bajo_terms if re.search(rf"\b{re.escape(t)}\b", normalized)])
        else:
            nivel_emocional = "Sin riesgo"
            risk_words = None


        keys = self._get_api_keys()
        if not keys:
            response_text = self._build_local_fallback(message, history, config, es_medio, es_bajo)
            self.chat_repo.save_conversation(patient_id, message, response_text, nivel_emocional, risk_words)
            return {
                "success": True,
                "respuesta": response_text,
                "fallback": True,
                "message": "GEMINI_API_KEY no configurada",
                "used": used_today + 1,
                "limit": daily_limit,
            }, 200

        model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
        contexto_riesgo = self._build_risk_context(es_medio, es_bajo)

        if es_medio or es_bajo:
            thinking_level = "medium"
        else:
            thinking_level = config.get("thinking_level") or "low"

        try:
            response_text = self._call_gemini_with_rotation(keys, model, message, history, config, contexto_riesgo, thinking_level)
            if not response_text or not response_text.strip():
                raise RuntimeError("Gemini devolvio texto vacio")
            if "[FUERA_DE_TEMA" in response_text or "[FUERA_DE_ALCANCE" in response_text:
                off_topic = (config.get("off_topic_response") or "").strip()
                response_text = off_topic or (
                    "Ese tema se sale un poco de mi alcance, pero si quieres "
                    "cuéntame cómo te has sentido últimamente."
                )
            self.chat_repo.save_conversation(patient_id, message, response_text, nivel_emocional, risk_words)
            return {
                "success": True,
                "respuesta": response_text,
                "used": used_today + 1,
                "limit": daily_limit,
            }, 200
        except Exception as exc:
            self.logger.exception("Error llamando Gemini: %s", exc)
            response_text = self._build_local_fallback(message, history, config, es_medio, es_bajo)
            self.chat_repo.save_conversation(patient_id, message, response_text, nivel_emocional, risk_words)
            return {
                "success": True,
                "respuesta": response_text,
                "fallback": True,
                "message": "No se pudo contactar Gemini",
                "used": used_today + 1,
                "limit": daily_limit,
            }, 200

    def _build_risk_context(self, es_medio=False, es_bajo=False):
        if es_medio:
            medium_response = (self._cached_config.get("medium_response") or "").strip()
            if medium_response:
                return medium_response
            return (
                "El paciente mostró señales de riesgo emocional medio. "
                "Responde con calidez y, si es natural, sugiere hablar con su profesional sin sonar alarmante."
            )
        if es_bajo:
            return (
                "El paciente mostró una señal leve de malestar. "
                "Responde con empatía y normalidad, sin alarmar."
            )
        return None

    def _call_gemini_with_rotation(self, keys, model, message, history, config, contexto_riesgo=None, thinking_level=None):
        total_keys = len(keys)
        start_index = self._key_index

        for attempt in range(total_keys):
            current_key = keys[self._key_index]
            try:
                response_text = self._call_gemini(current_key, model, message, history, config, contexto_riesgo, thinking_level)
                self.logger.info("Chatbot: respuesta generada por el modelo IA principal: %s", model)
                return response_text
            except RuntimeError as exc:
                error_str = str(exc)
                is_quota = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                if is_quota:
                    if total_keys > 1:
                        self._next_key(keys)
                        self.logger.warning(
                            "Key %s/%s agotó cuota (429). Rotando a key %s/%s.",
                            attempt + 1, total_keys,
                            self._key_index + 1, total_keys,
                        )
                        continue
                    break
                raise

        fallback_model = self._get_fallback_model()
        if keys and fallback_model and fallback_model != model:
            try:
                self.logger.warning(
                    "Modelo principal (%s) agotó cuota. Intentando modelo de respaldo: %s",
                    model, fallback_model,
                )
                response_text = self._call_gemini(
                    keys[0], fallback_model, message, history, config, contexto_riesgo, thinking_level
                )
                self.logger.info("Chatbot: respuesta generada por el modelo IA de respaldo: %s", fallback_model)
                return response_text
            except RuntimeError as exc:
                self.logger.warning("Modelo de respaldo (%s) también falló: %s", fallback_model, exc)

        raise RuntimeError("Todas las API keys agotaron su cuota por hoy, incluido el modelo de respaldo.")

    def _call_gemini_json(self, api_key, model, system_prompt, user_prompt, temperature=0.3, max_tokens=1600):
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": float(temperature),
                "maxOutputTokens": int(max_tokens),
            },
        }
        base_delay = GEMINI_RETRY_BASE_DELAY
        last_exc = None
        for attempt in range(1, GEMINI_RETRIES + 2):
            try:
                resp = requests.post(
                    GEMINI_URL_TEMPLATE.format(model=model),
                    json=payload,
                    headers={"x-goog-api-key": api_key},
                    timeout=20,
                )
                if resp.status_code in GEMINI_RETRYABLE_STATUS:
                    last_exc = RuntimeError(f"Gemini HTTP {resp.status_code}")
                    self.logger.warning("Gemini JSON HTTP %s intento %s/%s", resp.status_code, attempt, GEMINI_RETRIES + 1)
                    if attempt <= GEMINI_RETRIES:
                        time.sleep(base_delay * attempt)
                    continue
                if resp.status_code != 200:
                    body = resp.text[:2000]
                    self.logger.error("Gemini JSON respondio %s body: %s", resp.status_code, body)
                    last_exc = RuntimeError(f"Gemini HTTP {resp.status_code}: {body[:200]}")
                    if attempt <= GEMINI_RETRIES:
                        time.sleep(base_delay * attempt)
                    continue
                data = resp.json()
                text = self._extract_text(data)
                if not text:
                    raise RuntimeError("Gemini no devolvio texto")
                return text.strip()
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                self.logger.warning("Gemini JSON request error intento %s/%s: %s", attempt, GEMINI_RETRIES + 1, exc)
                if attempt <= GEMINI_RETRIES:
                    time.sleep(base_delay * attempt)
        raise RuntimeError(f"Gemini no disponible luego de reintentos: {last_exc}")

    def _build_local_fallback(self, message, history, config, es_medio=False, es_bajo=False):
        normalized = self._normalize_text(message)
        last_bot_message = self._last_bot_message(history)

        if es_bajo:
            bajo_options = [
                "Gracias por contarme eso. A veces nombrar lo que sentimos ya ayuda un poco. Que crees que esta influyendo en como te sientes hoy?",
                "Te escucho. Es valido sentirse asi de vez en cuando. Hay algo concreto que te haya estado pesando?",
                "Aprecio que compartas esto conmigo. Te gustaria contarme un poco mas sobre lo que esta pasando?",
            ]
            for option in self._rotate_options(bajo_options, message):
                if option != last_bot_message:
                    return option
            return bajo_options[0]

        if es_medio:
            medio_options = [
                "Gracias por compartir esto conmigo. Parece que hay algo que te está afectando más de lo habitual. ¿Qué tan seguido has estado sintiendo esto últimamente?",
                "Valoro que me cuentes cómo te sientes. A veces cuando algo nos pesa así, hablar con la persona indicada puede ayudar. ¿Has considerado comentarlo con tu profesional?",
                "Entiendo que esto puede ser difícil de llevar. Quiero recordarte que no estás sol@ en esto y que hay personas que pueden apoyarte. ¿Te gustaría que hablemos más sobre ello?",
            ]
            for option in self._rotate_options(medio_options, message):
                if option != last_bot_message:
                    return option
            return medio_options[0]

        if self._contains_any(normalized, ("ansioso", "ansiosa", "ansiedad", "nervioso", "nerviosa", "estres", "estresado", "estresada")):
            options = [
                "Se nota que esto te esta activando bastante. Para entenderlo mejor, que fue lo que disparo esa ansiedad hoy?",
                "Tiene sentido que te sientas asi si vienes con tanta tension. En que parte del dia lo sentiste mas fuerte?",
                "Gracias por decirlo; la ansiedad puede sentirse muy pesada. Que has intentado hasta ahora para calmarte un poco?",
            ]
        elif self._contains_any(normalized, ("triste", "solo", "sola", "llorar", "deprimido", "deprimida", "vacio", "vacia")):
            options = [
                "Eso suena doloroso y no tienes que minimizarlo. Desde cuando vienes sintiendote asi?",
                "Gracias por confiarme eso; parece que estas cargando algo importante. Que es lo que mas te esta pesando hoy?",
                "Siento que estes pasando por ese bajon. Hay alguien cercano con quien te sentirias seguro/a hablando hoy?",
            ]
        elif self._contains_any(normalized, ("dormir", "sueno", "insomnio", "cansado", "cansada", "agotado", "agotada")):
            options = [
                "El descanso afecta mucho como se siente todo lo demas. Como dormiste anoche?",
                "Ese cansancio puede volver el dia mucho mas dificil. Te pasa desde hace varios dias o fue algo puntual?",
                "Gracias por contarlo; dormir mal suele aumentar la carga emocional. Que suele pasar justo antes de que intentes dormir?",
            ]
        elif self._contains_any(normalized, ("comer", "apetito", "hambre", "nausea", "nauseas")):
            options = [
                "El apetito tambien puede reflejar como esta tu animo. Has notado si estas comiendo mas, menos o igual que antes?",
                "Gracias por mencionarlo; eso ayuda a entender mejor tu estado. Ese cambio de apetito empezo hoy o lleva mas tiempo?",
                "Tiene sentido revisarlo con calma. Como estuvo tu alimentacion durante el dia?",
            ]
        elif "?" in message:
            options = [
                "Buena pregunta. Para orientarte mejor, que te llevo a pensar en eso ahora?",
                "Puedo acompanarte a mirarlo paso a paso. Que parte de eso te preocupa mas?",
                "Entiendo la duda. Que respuesta esperarias encontrar o que necesitas decidir con esto?",
            ]
        else:
            configured_fallback = (config.get("fallback_response") or "").strip()
            options = [
                configured_fallback,
                "Gracias por contarmelo. Si tuvieras que ponerle nombre a lo que sientes ahora, cual seria?",
                "Te leo. Que fue lo mas importante o dificil de eso para ti?",
                "Quiero entenderte bien. Esto que cuentas te pasa seguido o empezo recientemente?",
            ]

        options = [o for o in options if o]
        if not options:
            options = ["Estoy aqui para escucharte. Como describirias tu estado de animo ahora?"]

        for option in self._rotate_options(options, message):
            if option != last_bot_message:
                return option
        return options[0]

    def _normalize_text(self, value):
        text = (value or "").lower()
        replacements = str.maketrans("\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1", "aeiouun")
        return text.translate(replacements)

    def _contains_any(self, text, terms):
        return any(term in text for term in terms)

    def _last_bot_message(self, history):
        for item in reversed(history or []):
            if item.get("tipo") == "bot":
                return (item.get("mensaje") or "").strip()
        return None

    def _rotate_options(self, options, seed_text):
        seed = sum(ord(char) for char in re.sub(r"\s+", "", seed_text or ""))
        start = seed % len(options)
        return options[start:] + options[:start]

    def _notify_high_risk(self, patient_id):
        patient_name = self._get_patient_name(patient_id) or f"Paciente #{patient_id}"
        titulo = "Alerta: el paciente requiere atención urgente"
        mensaje = f"Alerta: el paciente {patient_name} requiere atención urgente. Se detectaron palabras de riesgo alto en el chatbot."
        profesionales = self._get_assigned_professionals(patient_id)
        destinos = profesionales if profesionales else self._get_all_professional_ids()
        for profesional_id in destinos:
            self.appointment_repo.create_notification(profesional_id, "profesional", titulo, mensaje, "Alerta")
        self._send_risk_email(patient_id, patient_name, destinos, es_alto=True)

    def _send_risk_email(self, patient_id, patient_name, professional_ids, es_alto=False):
        site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
        patient_email = self.chat_repo.get_patient_email(patient_id)
        prof_emails = self.chat_repo.get_professional_emails(professional_ids)
        if not prof_emails:
            return
        nivel = "alto" if es_alto else "medio"
        asunto = f"PsyAI Connect — Alerta de riesgo {nivel}: {patient_name}"
        cta = f"{site_url}/aside-professional/patients.html"
        for email in prof_emails:
            ctx = {
                "nombre_profesional": email.split("@")[0].replace(".", " ").title(),
                "nombre_paciente": patient_name,
                "nivel_riesgo": nivel,
                "cta_link": cta,
            }
            html = render_to_string("emails/alerta_riesgo.html", ctx)
            msg = EmailMultiAlternatives(asunto, f"Alerta de riesgo {nivel}: el paciente {patient_name} requiere seguimiento.", to=[email])
            msg.attach_alternative(html, "text/html")
            try:
                msg.send(fail_silently=True)
            except Exception:
                self.logger.exception("Error enviando correo de riesgo %s a %s", nivel, email)

    def _get_assigned_professionals(self, patient_id):
        return self.chat_repo.get_assigned_professionals(patient_id)

    def _get_all_professional_ids(self):
        return self.chat_repo.get_all_professional_ids()

    def _ya_notificado_recientemente(self, patient_name, tipo, horas=12):
        return self.chat_repo.notificacion_reciente_existe(patient_name, tipo, horas)

    def _notify_medium_risk(self, patient_id, risk_words):
        patient_name = self._get_patient_name(patient_id) or f"Paciente #{patient_id}"

        if self._ya_notificado_recientemente(patient_name, "Seguimiento", horas=12):
            self.logger.info("Riesgo medio: ya se notificó a profesionales sobre %s en las últimas 12h, omitiendo.", patient_name)
            return

        titulo = "Seguimiento recomendado"
        mensaje = (
            f"El paciente {patient_name} mostró señales de riesgo medio en el chatbot "
            f"(palabras detectadas: {risk_words}). Se recomienda revisar su evolución reciente."
        )
        profesionales = self._get_assigned_professionals(patient_id)
        destinos = profesionales if profesionales else self._get_all_professional_ids()
        for profesional_id in destinos:
            self.appointment_repo.create_notification(profesional_id, "profesional", titulo, mensaje, "Seguimiento")
        self.logger.info("Notificación de seguimiento enviada a %d profesional(es) sobre %s", len(destinos), patient_name)
        self._send_risk_email(patient_id, patient_name, destinos, es_alto=False)

    def _get_patient_name(self, patient_id):
        return self.chat_repo.get_patient_name(patient_id)

    def _build_system_prompt(self, config, history, contexto_riesgo=None):
        system_prompt = (config.get("system_prompt") or SYSTEM_PROMPT_FALLBACK).strip()
        interaction_rules = (config.get("interaction_rules") or "").strip()
        tone = (config.get("tone") or "").strip()
        if interaction_rules:
            system_prompt = f"{system_prompt}\nReglas de interacción: {interaction_rules}"
        if tone:
            system_prompt = f"{system_prompt}\nTono de comunicación: {tone.lower()}."
        if contexto_riesgo:
            system_prompt = f"{system_prompt}\n\nCONTEXTO DE RIESGO DETECTADO: {contexto_riesgo}"
        if history:
            prompt_window = int(config.get("prompt_history_window") or 4)
            ultimos = history[-prompt_window:]
            if ultimos:
                resumen = " | ".join(
                    f"{'Paciente' if h['tipo'] == 'usuario' else 'Bot'}: {h['mensaje']}"
                    for h in ultimos
                )
                system_prompt = (
                    f"{system_prompt}\n\nCONTEXTO RECIENTE DE LA CONVERSACIÓN: {resumen}. "
                    "No repitas preguntas ya formuladas."
                )
        return f"{system_prompt}{_PROMPT_SUFFIX}"

    def _call_gemini(self, api_key, model, message, history, config, contexto_riesgo=None, thinking_level=None):
        system_prompt = self._build_system_prompt(config, history, contexto_riesgo)
        max_user_chars = int(config.get("max_tokens_user") or 1000)

        if thinking_level is None:
            thinking_level = config.get("thinking_level") or "low"
        if thinking_level == "none":
            thinking_level = None

        generation_config = {
            "temperature": float(config.get("temperature", 0.55)),
            "topP": float(config.get("top_p", 0.9)),
            "maxOutputTokens": int(config.get("max_tokens", 600)),
        }
        if thinking_level and self._model_supports_thinking(model):
            generation_config["thinkingConfig"] = {"thinkingLevel": thinking_level}

        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": self._build_contents(history, message, max_user_chars),
            "generationConfig": generation_config,
        }
        base_delay = GEMINI_RETRY_BASE_DELAY
        last_exc = None
        for attempt in range(1, GEMINI_RETRIES + 2):
            try:
                resp = requests.post(
                    GEMINI_URL_TEMPLATE.format(model=model),
                    json=payload,
                    headers={"x-goog-api-key": api_key},
                    timeout=8,
                )
                if resp.status_code in GEMINI_RETRYABLE_STATUS:
                    last_exc = RuntimeError(f"Gemini HTTP {resp.status_code}")
                    self.logger.warning("Gemini HTTP %s intento %s/%s", resp.status_code, attempt, GEMINI_RETRIES + 1)
                    if attempt <= GEMINI_RETRIES:
                        time.sleep(base_delay * attempt)
                    continue
                if resp.status_code != 200:
                    body = resp.text[:2000]
                    self.logger.error(
                        "Gemini respondio %s en intento %s/%s body: %s",
                        resp.status_code, attempt, GEMINI_RETRIES + 1, body,
                    )
                    last_exc = RuntimeError(f"Gemini HTTP {resp.status_code}: {body[:200]}")
                    if attempt <= GEMINI_RETRIES:
                        time.sleep(base_delay * attempt)
                    continue
                data = resp.json()
                text = self._extract_text(data)
                if not text:
                    raise RuntimeError("Gemini no devolvio texto")
                return text.strip()
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                self.logger.warning("Gemini request error intento %s/%s: %s", attempt, GEMINI_RETRIES + 1, exc)
                if attempt <= GEMINI_RETRIES:
                    time.sleep(base_delay * attempt)
        raise RuntimeError(f"Gemini no disponible luego de reintentos: {last_exc}")

    def _build_contents(self, history, message, max_user_chars=1000):
        contents = []
        gemini_window = int(self._cached_config.get("gemini_history_window", 12) if self._cached_config else 12)
        for item in (history or [])[-gemini_window:]:
            if not isinstance(item, dict):
                continue
            text = (item.get("mensaje") or "").strip()
            if not text:
                continue
            role = "model" if item.get("tipo") == "bot" else "user"
            history_limit = max_user_chars // 2
            if contents and contents[-1]["role"] == role:
                contents[-1]["parts"][0]["text"] += "\n" + text[:history_limit]
            else:
                contents.append({"role": role, "parts": [{"text": text[:history_limit]}]})
        while contents and contents[0]["role"] != "user":
            contents.pop(0)
        contents.append({"role": "user", "parts": [{"text": message[:max_user_chars]}]})
        return contents

    def _extract_text(self, data):
        parts = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        return "".join(part.get("text", "") for part in parts)

    @staticmethod
    def _model_supports_thinking(model):
        model_lower = model.lower()
        if "gemma" in model_lower:
            return False
        if any(m in model_lower for m in ("2.5-flash", "2.5-pro", "3-flash", "3.1-flash", "3.1-pro", "3.5-flash", "3.5-pro")):
            return True
        return False

    def get_history(self, patient_id):
        self.logger.info("get_history llamado con patient_id: %s", patient_id)
        historial = self.chat_repo.get_history(patient_id, today_only=True)
        self.logger.info("Historial recuperado: %s mensajes", len(historial))
        return {"success": True, "historial": historial}, 200
