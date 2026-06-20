import json

from app.repositories import chatbot_config_repository


DEFAULT_CONFIG = {
    "system_prompt": """Actua como un asistente de triaje psicologico para PsyAI Connect.
Tu objetivo es ser empatico, claro y breve. No des diagnosticos medicos, no reemplaces a un profesional de salud,
no indiques medicamentos y no afirmes que el usuario tiene una enfermedad.

Sigue este protocolo de preguntas en orden, adaptandote a lo que el usuario ya respondio:
1. Estado de animo.
2. Calidad del sueno.
3. Apetito.

Si detectas riesgo de autolesion, suicidio, intencion de hacerse dano o peligro inmediato, responde de inmediato
con apoyo de crisis y entrega estas lineas para Bello, Antioquia:
- Emergencias: llama al 123 ahora.
- ESE Hospital Mental de Antioquia, Bello: +57 (604) 444 8330.
Pide que contacte a una persona de confianza y que no se quede solo/a.

Responde siempre en espanol, con tono calido y profesional. Usa 2 a 4 frases completas y no cortes oraciones.""",
    "risk_terms": "[]",
    "crisis_response": "Siento mucho que estes pasando por esto. Si hay riesgo de autolesion o peligro inmediato, por favor llama ahora al 123 en Bello/Antioquia o pide a alguien cercano que lo haga por ti. Tambien puedes contactar al ESE Hospital Mental de Antioquia en Bello: +57 (604) 444 8330. No te quedes solo/a en este momento; busca a una persona de confianza y alejate de cualquier medio con el que puedas hacerte dano.",
    "fallback_response": "Gracias por contarmelo. Quiero acompanarte con calma: primero, ¿como describirias tu estado de animo hoy: tranquilo/a, triste, ansioso/a, irritable o algo distinto?",
    "tone": "calido y profesional",
    "interaction_rules": "Responde con empatía, mantén frases breves y no proporciones diagnósticos médicos.",
    "temperature": 0.55,
    "top_p": 0.9,
    "max_tokens": 600,
    "max_tokens_user": 1000,
    "daily_message_limit": 20,
}


def get_config():
    config = chatbot_config_repository.get_config()
    if not config:
        return DEFAULT_CONFIG.copy()
    
    result = {
        "system_prompt": config.get("system_prompt") or DEFAULT_CONFIG["system_prompt"],
        "tone": config.get("tone") or DEFAULT_CONFIG["tone"],
        "interaction_rules": config.get("interaction_rules") or DEFAULT_CONFIG["interaction_rules"],
        "risk_terms": config.get("risk_terms") if config.get("risk_terms") is not None else "[]",
        "crisis_response": config.get("crisis_response") or DEFAULT_CONFIG["crisis_response"],
        "fallback_response": config.get("fallback_response") or DEFAULT_CONFIG["fallback_response"],
        "temperature": config.get("temperature") if config.get("temperature") is not None else DEFAULT_CONFIG["temperature"],
        "top_p": config.get("top_p") if config.get("top_p") is not None else DEFAULT_CONFIG["top_p"],
        "max_tokens": config.get("max_tokens") if config.get("max_tokens") is not None else DEFAULT_CONFIG["max_tokens"],
        "max_tokens_user": config.get("max_tokens_user") if config.get("max_tokens_user") is not None else DEFAULT_CONFIG["max_tokens_user"],
        "daily_message_limit": config.get("daily_message_limit") if config.get("daily_message_limit") is not None else DEFAULT_CONFIG["daily_message_limit"],
    }
    
    if config.get("fecha_actualizacion"):
        result["fecha_actualizacion"] = config["fecha_actualizacion"].strftime("%d/%m/%Y %H:%M") if hasattr(config["fecha_actualizacion"], "strftime") else str(config["fecha_actualizacion"])
    if config.get("actualizado_por"):
        result["actualizado_por"] = config["actualizado_por"]
    
    return result


def save_config(data, admin_id):
    temperature = data.get("temperature")
    top_p = data.get("top_p")
    max_tokens = data.get("max_tokens")
    max_tokens_user = data.get("max_tokens_user")
    daily_message_limit = data.get("daily_message_limit")
    
    if temperature is not None:
        try:
            temperature = float(temperature)
            if temperature < 0 or temperature > 1:
                return {"success": False, "message": "Temperature debe estar entre 0 y 1"}, 400
        except (ValueError, TypeError):
            return {"success": False, "message": "Temperature debe ser un número entre 0 y 1"}, 400
    
    if top_p is not None:
        try:
            top_p = float(top_p)
            if top_p < 0 or top_p > 1:
                return {"success": False, "message": "Top P debe estar entre 0 y 1"}, 400
        except (ValueError, TypeError):
            return {"success": False, "message": "Top P debe ser un número entre 0 y 1"}, 400
    
    if max_tokens is not None:
        try:
            max_tokens = int(max_tokens)
            if max_tokens < 100 or max_tokens > 2000:
                return {"success": False, "message": "Max tokens del bot debe estar entre 100 y 2000"}, 400
        except (ValueError, TypeError):
            return {"success": False, "message": "Max tokens del bot debe ser un número entre 100 y 2000"}, 400
    
    if max_tokens_user is not None:
        try:
            max_tokens_user = int(max_tokens_user)
            if max_tokens_user < 200 or max_tokens_user > 4000:
                return {"success": False, "message": "Max tokens del usuario debe estar entre 200 y 4000"}, 400
        except (ValueError, TypeError):
            return {"success": False, "message": "Max tokens del usuario debe ser un número entre 200 y 4000"}, 400
    
    if daily_message_limit is not None:
        try:
            daily_message_limit = int(daily_message_limit)
            if daily_message_limit < 1 or daily_message_limit > 200:
                return {"success": False, "message": "El limite diario debe estar entre 1 y 200"}, 400
        except (ValueError, TypeError):
            return {"success": False, "message": "El limite diario debe ser un numero entero"}, 400

    incoming_risk = data.get("risk_terms")
    if incoming_risk is not None and incoming_risk.strip() in ("[]", ""):
        current_config = chatbot_config_repository.get_config()
        if current_config:
            current_risk = current_config.get("risk_terms")
            if current_risk and current_risk.strip() not in ("[]", ""):
                try:
                    parsed = json.loads(current_risk)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        data["risk_terms"] = current_risk
                except (json.JSONDecodeError, TypeError):
                    pass

    rowcount = chatbot_config_repository.save_config(data, admin_id)
    if rowcount >= 0:
        return {"success": True, "message": "Configuración guardada correctamente"}, 200
    return {"success": False, "message": "Error al guardar configuración"}, 500


def save_risk_terms_only(risk_terms_str, admin_id):
    rowcount = chatbot_config_repository.save_risk_terms_only(risk_terms_str, admin_id)
    if rowcount >= 0:
        return {"success": True, "message": "Palabras de riesgo guardadas"}, 200
    return {"success": False, "message": "Error al guardar palabras de riesgo"}, 500


def clear_risk_terms(admin_id):
    from app.utils.db import db_cursor
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE ChatbotConfig SET risk_terms = '', fecha_actualizacion = NOW() WHERE id = 1"
        )
        conn.commit()
    return {"success": True, "message": "Palabras de riesgo eliminadas"}, 200


def get_detected_risk_words():
    """
    Returns all risk words detected in patient conversations, grouped by word,
    with highest level seen, count, and unique patient names.
    Returns list: [{palabra, nivel, count, pacientes}, ...]
    If view doesn't exist, returns [].
    """
    from app.utils.db import db_cursor
    try:
        with db_cursor(dictionary=True) as (_, cursor):
            cursor.execute("""
                SELECT nombre, palabrasRiesgoDetectadas, nivelEmocionalDetectado
                FROM vistahistorialchatbot
                WHERE palabrasRiesgoDetectadas IS NOT NULL
                  AND palabrasRiesgoDetectadas != ''
            """)
            rows = cursor.fetchall()
    except Exception as e:
        estr = str(e)
        if "1146" in estr or "doesn't exist" in estr:
            return []
        raise

    NIVEL_PRECEDENCE = {"Alto": 3, "Medio": 2, "Bajo": 1}
    word_data = {}

    for row in rows:
        detected_raw = row.get("palabrasRiesgoDetectadas", "") or ""
        detected_words = [w.strip().lower() for w in detected_raw.split(",") if w.strip()]
        level = row.get("nivelEmocionalDetectado", "Bajo") or "Bajo"
        paciente = row.get("nombre", "Paciente") or "Paciente"

        for word in detected_words:
            if word not in word_data:
                word_data[word] = {
                    "palabra": word,
                    "nivel": level,
                    "nivel_priority": NIVEL_PRECEDENCE.get(level, 1),
                    "count": 0,
                    "pacientes": set()
                }
            else:
                new_priority = NIVEL_PRECEDENCE.get(level, 1)
                if new_priority > word_data[word]["nivel_priority"]:
                    word_data[word]["nivel"] = level
                    word_data[word]["nivel_priority"] = new_priority

            word_data[word]["count"] += 1
            word_data[word]["pacientes"].add(paciente)

    return [
        {
            "palabra": v["palabra"],
            "nivel": v["nivel"],
            "count": v["count"],
            "pacientes": sorted(v["pacientes"])
        }
        for v in word_data.values()
    ]
