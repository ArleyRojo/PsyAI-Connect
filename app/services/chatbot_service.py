import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.repositories import chat_repository, patient_repository, appointment_repository, chatbot_config_repository
from app.services import chatbot_config_service
from app.utils.db import db_cursor

logger = logging.getLogger(__name__)

GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
GEMINI_RETRIES = 2
GEMINI_RETRY_BASE_DELAY = 0.6
SYSTEM_PROMPT_FALLBACK = "Actua como un asistente de triaje psicologico para PsyAI Connect."
CONFIG_CACHE_TTL_SECONDS = 30

_cached_config_version = None
_cached_config = None
_cached_system_prompt = None
_cached_config_ts = 0.0

# ── Rotación de API keys ──────────────────────────────────────────────────────
# Para activar: agrega en .env -> GEMINI_API_KEYS=key1,key2,key3,...
# Si GEMINI_API_KEYS está vacío, se usa GEMINI_API_KEY como antes (comportamiento actual).
# Cada key es un proyecto distinto de Google AI Studio con su propia cuota de 1,500 req/día.
# El sistema rota automáticamente a la siguiente key cuando recibe un 429.
_key_index = 0  # índice de la key activa actualmente


def _get_api_keys() -> list[str]:
    """
    Retorna la lista de API keys disponibles.
    Primero intenta GEMINI_API_KEYS (varias keys separadas por coma).
    Si no existe, usa GEMINI_API_KEY (una sola key — comportamiento original).
    """
    multi = os.getenv("GEMINI_API_KEYS", "").strip()
    if multi:
        keys = [k.strip() for k in multi.split(",") if k.strip()]
        if keys:
            return keys
    single = os.getenv("GEMINI_API_KEY", "").strip()
    return [single] if single else []


def _next_key(keys: list[str]) -> str | None:
    """
    Rota al siguiente key disponible y lo retorna.
    Actualiza el índice global _key_index.
    """
    global _key_index
    if not keys:
        return None
    _key_index = (_key_index + 1) % len(keys)
    return keys[_key_index]


# ─────────────────────────────────────────────────────────────────────────────

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


def _now_ts():
    return datetime.now(timezone.utc).timestamp()


def _get_chatbot_config():
    global _cached_config_version, _cached_config, _cached_config_ts
    now = _now_ts()
    if _cached_config is not None and now - _cached_config_ts < CONFIG_CACHE_TTL_SECONDS:
        return _cached_config, _cached_config_version
    try:
        row = chatbot_config_repository.get_config()
    except Exception:
        row = None
    version = None
    if row and isinstance(row, dict):
        version = row.get("fecha_actualizacion")
        if hasattr(version, "isoformat"):
            version = version.isoformat()
        version = str(version) if version is not None else None
    if version == _cached_config_version and _cached_config is not None:
        return _cached_config, _cached_config_version
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
    result.setdefault("daily_message_limit", result.get("daily_message_limit", 20))
    _cached_config = result
    _cached_config_version = version
    _cached_config_ts = now
    return _cached_config, _cached_config_version


def build_response(patient_id, message):
    message = (message or "").strip()
    if not message:
        return {"success": False, "message": "Mensaje requerido"}, 400

    config, _ = _get_chatbot_config()
    daily_limit = int(config.get("daily_message_limit") or 20)
    used_today = chat_repository.count_today_messages(patient_id)
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

    history = chat_repository.get_history(patient_id, today_only=False, limit=12)

    try:
        risk_list = json.loads(config.get("risk_terms") or "[]")
    except Exception:
        risk_list = []

    alto_terms  = [r["palabra"].strip().lower() for r in risk_list if r.get("nivel") == "Alto"  and r.get("palabra")]
    medio_terms = [r["palabra"].strip().lower() for r in risk_list if r.get("nivel") == "Medio" and r.get("palabra")]
    bajo_terms  = [r["palabra"].strip().lower() for r in risk_list if r.get("nivel") == "Bajo"  and r.get("palabra")]

    normalized = message.lower()
    es_alto  = any(t in normalized for t in alto_terms)
    es_medio = any(t in normalized for t in medio_terms)
    es_bajo  = any(t in normalized for t in bajo_terms)

    if es_alto:
        nivel_emocional = "Alto"
        risk_words = ",".join([t for t in alto_terms if t in normalized])
        _notify_high_risk(patient_id)
        chat_repository.save_conversation(
            patient_id, message, config.get("crisis_response", ""), nivel_emocional, risk_words
        )
        return {
            "success": True,
            "respuesta": config.get("crisis_response", ""),
            "risk_detected": True,
            "used": used_today + 1,
            "limit": daily_limit,
        }, 200

    keys = _get_api_keys()
    if not keys:
        nivel_emocional, risk_words = _evaluate_risk_level(es_medio, es_bajo, medio_terms, bajo_terms, normalized)
        response_text = _build_local_fallback(message, history, config)
        chat_repository.save_conversation(patient_id, message, response_text, nivel_emocional, risk_words)
        return {
            "success": True,
            "respuesta": response_text,
            "fallback": True,
            "message": "GEMINI_API_KEY no configurada",
            "used": used_today + 1,
            "limit": daily_limit,
        }, 200

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite").strip() or "gemini-2.5-flash-lite"

    try:
        response_text = _call_gemini_with_rotation(keys, model, message, history or [], config)
        nivel_emocional, risk_words = _evaluate_risk_level(es_medio, es_bajo, medio_terms, bajo_terms, normalized)
        chat_repository.save_conversation(patient_id, message, response_text, nivel_emocional, risk_words)
        return {
            "success": True,
            "respuesta": response_text,
            "used": used_today + 1,
            "limit": daily_limit,
        }, 200
    except Exception as exc:
        logger.exception("Error llamando Gemini: %s", exc)
        nivel_emocional, risk_words = _evaluate_risk_level(es_medio, es_bajo, medio_terms, bajo_terms, normalized)
        response_text = _build_local_fallback(message, history, config)
        chat_repository.save_conversation(patient_id, message, response_text, nivel_emocional, risk_words)
        return {
            "success": True,
            "respuesta": response_text,
            "fallback": True,
            "message": "No se pudo contactar Gemini",
            "used": used_today + 1,
            "limit": daily_limit,
        }, 200


def _call_gemini_with_rotation(keys: list[str], model: str, message: str, history: list, config: dict) -> str:
    """
    Intenta llamar a Gemini usando la key activa.
    Si recibe 429 (cuota agotada), rota a la siguiente key y reintenta.
    Recorre todas las keys disponibles antes de rendirse.
    """
    global _key_index
    total_keys = len(keys)
    start_index = _key_index

    for attempt in range(total_keys):
        current_key = keys[_key_index]
        try:
            return call_gemini(current_key, model, message, history, config)
        except RuntimeError as exc:
            error_str = str(exc)
            is_quota = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
            if is_quota and total_keys > 1:
                next_key = _next_key(keys)
                logger.warning(
                    "Key %s/%s agotó cuota (429). Rotando a key %s/%s.",
                    attempt + 1, total_keys,
                    _key_index + 1, total_keys,
                )
            else:
                raise  # error no recuperable o solo hay 1 key

    raise RuntimeError("Todas las API keys agotaron su cuota por hoy.")


def _evaluate_risk_level(is_medio, is_bajo, medio_terms, bajo_terms, normalized):
    if is_medio:
        return "Medio", ",".join([t for t in medio_terms if t in normalized])
    if is_bajo:
        return "Bajo", ",".join([t for t in bajo_terms if t in normalized])
    return "Sin riesgo", None


def _build_local_fallback(message, history, config):
    normalized = _normalize_text(message)
    last_bot_message = _last_bot_message(history)

    if _contains_any(normalized, ("ansioso", "ansiosa", "ansiedad", "nervioso", "nerviosa", "estres", "estresado", "estresada")):
        options = [
            "Se nota que esto te esta activando bastante. Para entenderlo mejor, que fue lo que disparo esa ansiedad hoy?",
            "Tiene sentido que te sientas asi si vienes con tanta tension. En que parte del dia lo sentiste mas fuerte?",
            "Gracias por decirlo; la ansiedad puede sentirse muy pesada. Que has intentado hasta ahora para calmarte un poco?",
        ]
    elif _contains_any(normalized, ("triste", "solo", "sola", "llorar", "deprimido", "deprimida", "vacio", "vacia")):
        options = [
            "Eso suena doloroso y no tienes que minimizarlo. Desde cuando vienes sintiendote asi?",
            "Gracias por confiarme eso; parece que estas cargando algo importante. Que es lo que mas te esta pesando hoy?",
            "Siento que estes pasando por ese bajon. Hay alguien cercano con quien te sentirias seguro/a hablando hoy?",
        ]
    elif _contains_any(normalized, ("dormir", "sueno", "insomnio", "cansado", "cansada", "agotado", "agotada")):
        options = [
            "El descanso afecta mucho como se siente todo lo demas. Como dormiste anoche?",
            "Ese cansancio puede volver el dia mucho mas dificil. Te pasa desde hace varios dias o fue algo puntual?",
            "Gracias por contarlo; dormir mal suele aumentar la carga emocional. Que suele pasar justo antes de que intentes dormir?",
        ]
    elif _contains_any(normalized, ("comer", "apetito", "hambre", "nausea", "nauseas")):
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

    for option in _rotate_options(options, message):
        if option != last_bot_message:
            return option
    return options[0]


def _normalize_text(value):
    text = (value or "").lower()
    replacements = str.maketrans("\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1", "aeiouun")
    return text.translate(replacements)


def _contains_any(text, terms):
    return any(term in text for term in terms)


def _last_bot_message(history):
    for item in reversed(history or []):
        if item.get("tipo") == "bot":
            return (item.get("mensaje") or "").strip()
    return None


def _rotate_options(options, seed_text):
    seed = sum(ord(char) for char in re.sub(r"\s+", "", seed_text or ""))
    start = seed % len(options)
    return options[start:] + options[:start]


def _notify_high_risk(patient_id):
    patient_name = _get_patient_name(patient_id) or f"Paciente #{patient_id}"
    titulo = "Alerta: el paciente requiere atención urgente"
    mensaje = f"Alerta: el paciente {patient_name} requiere atención urgente. Se detectaron palabras de riesgo alto en el chatbot."
    profesionales = _get_assigned_professionals(patient_id)

    if profesionales:
        for profesional_id in profesionales:
            appointment_repository.create_notification(profesional_id, 'profesional', titulo, mensaje, 'Alerta')
        return

    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute("SELECT idUsuario FROM Register WHERE rol = 'profesional'")
        todos = cursor.fetchall()
        for row in todos:
            appointment_repository.create_notification(row['idUsuario'], 'profesional', titulo, mensaje, 'Alerta')


def _get_assigned_professionals(patient_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT idProfesional FROM PacientesProfesional WHERE idPaciente = %s",
            (patient_id,),
        )
        return [row['idProfesional'] for row in cursor.fetchall() if row.get('idProfesional')]


def _get_patient_name(patient_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT nombre FROM Register WHERE idUsuario = %s",
            (patient_id,),
        )
        row = cursor.fetchone()
        return row['nombre'] if row else None


def _build_system_prompt(config, history):
    system_prompt = (config.get("system_prompt") or SYSTEM_PROMPT_FALLBACK).strip()
    interaction_rules = (config.get("interaction_rules") or "").strip()
    tone = (config.get("tone") or "").strip()
    if interaction_rules:
        system_prompt = f"{system_prompt}\nReglas de interacción: {interaction_rules}"
    if tone:
        system_prompt = f"{system_prompt}\nTono de comunicación: {tone.lower()}."
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


def call_gemini(api_key, model, message, history, config):
    system_prompt = _build_system_prompt(config, history)
    max_user_chars = int(config.get("max_tokens_user") or 1000)
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": _build_contents(history, message, max_user_chars),
        "generationConfig": {
            "temperature": float(config.get("temperature", 0.55)),
            "topP": float(config.get("top_p", 0.9)),
            "maxOutputTokens": int(config.get("max_tokens", 600)),
        },
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
                text = _extract_text(data)
                if not text:
                    raise RuntimeError("Gemini no devolvio texto")
                return text.strip()
        except HTTPError as exc:
            last_exc = exc
            status = getattr(exc, "code", None)
            if status not in GEMINI_RETRYABLE_STATUS:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Gemini HTTP {status}: {detail}") from exc
            logger.warning("Gemini HTTP %s intento %s/%s", status, attempt, GEMINI_RETRIES + 1)
            if attempt <= GEMINI_RETRIES:
                time.sleep(base_delay * attempt)
        except URLError as exc:
            last_exc = exc
            logger.warning("Gemini URLError intento %s/%s: %s", attempt, GEMINI_RETRIES + 1, exc.reason)
            if attempt <= GEMINI_RETRIES:
                time.sleep(base_delay * attempt)
    raise RuntimeError(f"Gemini no disponible luego de reintentos: {last_exc}")


def _call_gemini(api_key, model, message, history, config):
    return call_gemini(api_key, model, message, history, config)


def _build_contents(history, message, max_user_chars=1000):
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


def _extract_text(data):
    parts = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    return "".join(part.get("text", "") for part in parts)


def get_history(patient_id):
    logger.info(f"get_history llamado con patient_id: {patient_id}")
    historial = chat_repository.get_history(patient_id, today_only=True)
    logger.info(f"Historial recuperado: {len(historial)} mensajes")
    return {"success": True, "historial": historial}, 200