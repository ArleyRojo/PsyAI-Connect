import json
import logging
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.repositories import chat_repository, patient_repository, appointment_repository
from app.services import chatbot_config_service
from app.utils.db import db_cursor

logger = logging.getLogger(__name__)

GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _get_config():
    try:
        return chatbot_config_service.get_config()
    except Exception:
        return {
            "system_prompt": "Actua como un asistente de triaje psicologico para PsyAI Connect.",
            "risk_terms": "[]",
            "crisis_response": "Si hay riesgo, llama al 123.",
            "fallback_response": "¿Cómo te sientes hoy?",
            "temperature": 0.55,
            "top_p": 0.9,
            "max_tokens": 420,
            "daily_message_limit": 20,
        }


def build_response(patient_id, message):
    message = (message or "").strip()
    if not message:
        return {"success": False, "message": "Mensaje requerido"}, 400

    config = _get_config()
    daily_limit = int(config.get("daily_message_limit") or 20)
    used_today = chat_repository.count_today_messages(patient_id)
    if used_today >= daily_limit:
        return {
            "success": False,
            "limit_reached": True,
            "used": used_today,
            "limit": daily_limit,
            "message": f"Alcanzaste el limite de {daily_limit} mensajes por hoy. Vuelve manana.",
        }, 429

    history = chat_repository.get_history(patient_id, today_only=False)

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

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        nivel_emocional, risk_words = _evaluate_risk_level(es_medio, es_bajo, medio_terms, bajo_terms, normalized)
        response_text = _build_local_fallback(message, history, config)
        chat_repository.save_conversation(
            patient_id, message, response_text, nivel_emocional, risk_words
        )
        return {
            "success": True,
            "respuesta": response_text,
            "fallback": True,
            "message": "GEMINI_API_KEY no configurada",
            "used": used_today + 1,
            "limit": daily_limit,
        }, 200

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    try:
        response_text = _call_gemini(api_key, model, message, history or [], config)
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
        chat_repository.save_conversation(
            patient_id, message, response_text, nivel_emocional, risk_words
        )
        return {
            "success": True,
            "respuesta": response_text,
            "fallback": True,
            "message": "No se pudo contactar Gemini",
            "used": used_today + 1,
            "limit": daily_limit,
        }, 200


def _evaluate_risk_level(is_medio, is_bajo, medio_terms, bajo_terms, normalized):
    if is_medio:
        return "Medio", ",".join([t for t in medio_terms if t in normalized])
    if is_bajo:
        return "Bajo", ",".join([t for t in bajo_terms if t in normalized])
    # Cambio: los mensajes neutros ya no se clasifican como riesgo bajo.
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

    options = [option for option in options if option]
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


def _call_gemini(api_key, model, message, history, config):
    system_prompt = config.get("system_prompt", "") or ""

    interaction_rules = config.get("interaction_rules")
    if interaction_rules:
        system_prompt = f"{system_prompt}\nReglas de interacción: {interaction_rules}"

    tone = config.get("tone")
    if tone:
        system_prompt = f"{system_prompt}\nTono de comunicación: {tone.lower()}."

    # Contexto emocional reciente de la conversación
    if history:
        ultimos = history[-6:]  # últimos 3 pares usuario / bot
        if ultimos:
            resumen = " | ".join(
                f"{'Paciente' if h['tipo'] == 'usuario' else 'Bot'}: {h['mensaje']}"
                for h in ultimos
            )
            system_prompt += (
                f"\n\nCONTEXTO RECIENTE DE LA CONVERSACIÓN: {resumen}. "
                "Ten esto en cuenta para no repetir preguntas ya hechas y mantener coherencia emocional."
            )

    # Few-shot examples y comportamiento obligatorio
    system_prompt += """

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

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": _build_contents(history, message),
        "generationConfig": {
            "temperature": config.get("temperature", 0.75),
            "topP": config.get("top_p", 0.92),
            "maxOutputTokens": config.get("max_tokens", 420),
        },
    }
    req = Request(
        GEMINI_URL_TEMPLATE.format(model=model),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=12) as res:
            data = json.loads(res.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Gemini network error: {exc.reason}") from exc

    text = _extract_text(data)
    if not text:
        raise RuntimeError("Gemini no devolvio texto")
    return text.strip()



def _build_contents(history, message):
    contents = []
    for item in history[-20:]:
        if not isinstance(item, dict):
            continue
        text = (item.get("mensaje") or "").strip()
        if not text:
            continue
        role = "model" if item.get("tipo") == "bot" else "user"
        contents.append({"role": role, "parts": [{"text": text[:1000]}]})
    contents.append({"role": "user", "parts": [{"text": message[:2000]}]})
    return contents


def _extract_text(data):
    parts = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    return "".join(part.get("text", "") for part in parts)


def get_history(patient_id):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"get_history llamado con patient_id: {patient_id}")
    historial = chat_repository.get_history(patient_id, today_only=True)
    logger.info(f"Historial recuperado: {len(historial)} mensajes")
    return {"success": True, "historial": historial}, 200
