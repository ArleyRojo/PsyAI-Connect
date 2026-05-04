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
    "max_tokens": 420,
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
            if max_tokens < 100 or max_tokens > 1000:
                return {"success": False, "message": "Max tokens debe estar entre 100 y 1000"}, 400
        except (ValueError, TypeError):
            return {"success": False, "message": "Max tokens debe ser un número entre 100 y 1000"}, 400
    
    rowcount = chatbot_config_repository.save_config(data, admin_id)
    if rowcount >= 0:
        return {"success": True, "message": "Configuración guardada correctamente"}, 200
    return {"success": False, "message": "Error al guardar configuración"}, 500


def clear_risk_terms(admin_id):
    from app.utils.db import db_cursor
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE ChatbotConfig SET risk_terms = '', fecha_actualizacion = NOW() WHERE id = 1"
        )
        conn.commit()
    return {"success": True, "message": "Palabras de riesgo eliminadas"}, 200