import json
import logging
import os
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
        }


def build_response(patient_id, message):
    message = (message or "").strip()
    if not message:
        return {"success": False, "message": "Mensaje requerido"}, 400

    config = _get_config()
    history = chat_repository.get_history(patient_id, today_only=True)

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
        return {"success": True, "respuesta": config.get("crisis_response", ""), "risk_detected": True}, 200

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        nivel_emocional, risk_words = _evaluate_risk_level(es_medio, es_bajo, medio_terms, bajo_terms, normalized)
        response_text = config.get("fallback_response", "") or config.get("empathetic_message", "Lo siento, no pude procesar tu mensaje ahora.")
        chat_repository.save_conversation(
            patient_id, message, response_text, nivel_emocional, risk_words
        )
        return {
            "success": True,
            "respuesta": response_text,
            "fallback": True,
            "message": "GEMINI_API_KEY no configurada",
        }, 200

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    try:
        response_text = _call_gemini(api_key, model, message, history or [], config)
        nivel_emocional, risk_words = _evaluate_risk_level(es_medio, es_bajo, medio_terms, bajo_terms, normalized)
        chat_repository.save_conversation(patient_id, message, response_text, nivel_emocional, risk_words)
        return {"success": True, "respuesta": response_text}, 200
    except Exception as exc:
        logger.exception("Error llamando Gemini: %s", exc)
        nivel_emocional, risk_words = _evaluate_risk_level(es_medio, es_bajo, medio_terms, bajo_terms, normalized)
        response_text = config.get("fallback_response", "") or config.get("empathetic_message", "Lo siento, no pude procesar tu mensaje ahora.")
        chat_repository.save_conversation(
            patient_id, message, response_text, nivel_emocional, risk_words
        )
        return {
            "success": True,
            "respuesta": response_text,
            "fallback": True,
            "message": "No se pudo contactar Gemini",
        }, 200


def _evaluate_risk_level(is_medio, is_bajo, medio_terms, bajo_terms, normalized):
    if is_medio:
        return "Medio", ",".join([t for t in medio_terms if t in normalized])
    if is_bajo:
        return "Bajo", ",".join([t for t in bajo_terms if t in normalized])
    return "Bajo", None


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
    tone = config.get("tone")
    if tone:
        system_prompt = f"Comunica con un tono {tone.lower()}.\n{system_prompt}"

    interaction_rules = config.get("interaction_rules")
    if interaction_rules:
        system_prompt = f"{system_prompt}\nReglas de interacción: {interaction_rules}"

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}] },
        "contents": _build_contents(history, message),
        "generationConfig": {
            "temperature": config.get("temperature", 0.55),
            "topP": config.get("top_p", 0.9),
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
    for item in history[-10:]:
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


def _has_self_harm_risk(text, risk_terms):
    normalized = (text or "").lower()
    return any(term in normalized for term in risk_terms)


def _extract_risk_words(text, risk_terms):
    normalized = (text or "").lower()
    found = [term for term in risk_terms if term in normalized]
    return ",".join(found) if found else None


def get_history(patient_id):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"get_history llamado con patient_id: {patient_id}")
    historial = chat_repository.get_history(patient_id, today_only=True)
    logger.info(f"Historial recuperado: {len(historial)} mensajes")
    return {"success": True, "historial": historial}, 200
