import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.repositories.chat_repository import ChatRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.chatbot_config_repository import ChatbotConfigRepository

GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
GEMINI_RETRIES = 2
GEMINI_RETRY_BASE_DELAY = 0.6
SYSTEM_PROMPT_FALLBACK = "Actua como un asistente de triaje psicologico para PsyAI Connect."
CONFIG_CACHE_TTL_SECONDS = 30

_PROMPT_SUFFIX = """

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
"""


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

    def _now_ts(self):
        return datetime.now(timezone.utc).timestamp()

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
                "fallback_response": "¿Cómo te sientes hoy?",
                "temperature": 0.55,
                "top_p": 0.9,
                "max_tokens": 600,
                "max_tokens_user": 1000,
                "daily_message_limit": 20,
                "thinking_level": None,
                "tone": None,
                "interaction_rules": None,
            }
        result.setdefault("risk_terms", result.get("risk_terms") or "[]")
        result.setdefault("crisis_response", result.get("crisis_response") or "")
        result.setdefault("fallback_response", result.get("fallback_response") or "")
        result.setdefault("temperature", result.get("temperature", 0.55))
        result.setdefault("top_p", result.get("top_p", 0.9))
        result.setdefault("max_tokens", result.get("max_tokens", 600))
        result.setdefault("max_tokens_user", result.get("max_tokens_user", 1000))
        result.setdefault("thinking_level", result.get("thinking_level") or None)
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
                    "asignado o llama a la línea de crisis: 106."
                ),
            }, 429

        history = self.chat_repo.get_history(patient_id, today_only=False, limit=12)

        try:
            risk_list = json.loads(config.get("risk_terms") or "[]")
        except Exception:
            risk_list = []

        alto_terms = [r["palabra"].strip().lower() for r in risk_list if r.get("nivel") == "Alto" and r.get("palabra")]
        medio_terms = [r["palabra"].strip().lower() for r in risk_list if r.get("nivel") == "Medio" and r.get("palabra")]
        bajo_terms = [r["palabra"].strip().lower() for r in risk_list if r.get("nivel") == "Bajo" and r.get("palabra")]

        normalized = message.lower()
        es_alto = any(t in normalized for t in alto_terms)
        es_medio = any(t in normalized for t in medio_terms)
        es_bajo = any(t in normalized for t in bajo_terms)

        if es_alto:
            nivel_emocional = "Alto"
            risk_words = ",".join([t for t in alto_terms if t in normalized])
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
            risk_words = ",".join([t for t in medio_terms if t in normalized])
            self._notify_medium_risk(patient_id, risk_words)
        elif es_bajo:
            nivel_emocional = "Bajo"
            risk_words = ",".join([t for t in bajo_terms if t in normalized])
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

        model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip() or "gemini-3.1-flash-lite"
        contexto_riesgo = self._build_risk_context(es_medio, es_bajo)

        if es_medio or es_bajo:
            thinking_level = "medium"
        else:
            thinking_level = None

        try:
            response_text = self._call_gemini_with_rotation(keys, model, message, history or [], config, contexto_riesgo, thinking_level)
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
                return self._call_gemini(current_key, model, message, history, config, contexto_riesgo, thinking_level)
            except RuntimeError as exc:
                error_str = str(exc)
                is_quota = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                if is_quota and total_keys > 1:
                    self._next_key(keys)
                    self.logger.warning(
                        "Key %s/%s agotó cuota (429). Rotando a key %s/%s.",
                        attempt + 1, total_keys,
                        self._key_index + 1, total_keys,
                    )
                else:
                    raise

        raise RuntimeError("Todas las API keys agotaron su cuota por hoy.")

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
            configured_fallback = (config.get("fallback_response") or config.get("empathetic_message") or "").strip()
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
            self.appointment_repo.create_notification(profesional_id, 'profesional', titulo, mensaje, 'Alerta')

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
            self.appointment_repo.create_notification(profesional_id, 'profesional', titulo, mensaje, 'Seguimiento')
        self.logger.info("Notificación de seguimiento enviada a %d profesional(es) sobre %s", len(destinos), patient_name)

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
            ultimos = history[-4:]
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
            thinking_level = config.get("thinking_level")
        if thinking_level is None:
            thinking_level = os.getenv("GEMINI_THINKING_LEVEL", "low").strip() or "low"

        generation_config = {
            "temperature": float(config.get("temperature", 0.55)),
            "topP": float(config.get("top_p", 0.9)),
            "maxOutputTokens": int(config.get("max_tokens", 600)),
        }
        if thinking_level:
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
                req = Request(
                    GEMINI_URL_TEMPLATE.format(model=model),
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": api_key,
                    },
                    method="POST",
                )
                with urlopen(req, timeout=8) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    text = self._extract_text(data)
                    if not text:
                        raise RuntimeError("Gemini no devolvio texto")
                    return text.strip()
            except HTTPError as exc:
                last_exc = exc
                status = getattr(exc, "code", None)
                if status not in GEMINI_RETRYABLE_STATUS:
                    detail = exc.read().decode("utf-8", errors="replace")
                    raise RuntimeError(f"Gemini HTTP {status}: {detail}") from exc
                self.logger.warning("Gemini HTTP %s intento %s/%s", status, attempt, GEMINI_RETRIES + 1)
                if attempt <= GEMINI_RETRIES:
                    time.sleep(base_delay * attempt)
            except URLError as exc:
                last_exc = exc
                self.logger.warning("Gemini URLError intento %s/%s: %s", attempt, GEMINI_RETRIES + 1, exc.reason)
                if attempt <= GEMINI_RETRIES:
                    time.sleep(base_delay * attempt)
        raise RuntimeError(f"Gemini no disponible luego de reintentos: {last_exc}")

    def _build_contents(self, history, message, max_user_chars=1000):
        contents = []
        for item in (history or [])[-12:]:
            if not isinstance(item, dict):
                continue
            text = (item.get("mensaje") or "").strip()
            if not text:
                continue
            role = "model" if item.get("tipo") == "bot" else "user"
            history_limit = max_user_chars // 2
            contents.append({"role": role, "parts": [{"text": text[:history_limit]}]})
        contents.append({"role": "user", "parts": [{"text": message[:max_user_chars]}]})
        return contents

    def _extract_text(self, data):
        parts = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        return "".join(part.get("text", "") for part in parts)

    def get_history(self, patient_id):
        self.logger.info("get_history llamado con patient_id: %s", patient_id)
        historial = self.chat_repo.get_history(patient_id, today_only=True)
        self.logger.info("Historial recuperado: %s mensajes", len(historial))
        return {"success": True, "historial": historial}, 200



