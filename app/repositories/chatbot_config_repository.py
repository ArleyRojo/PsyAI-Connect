from datetime import datetime
from sqlalchemy import text, func
from app.database.session import db_session
from app.models.chatbot_config import ChatbotConfig

CONFIG_COLUMNS = {
    "system_prompt": "system_prompt",
    "tone": "tone",
    "interaction_rules": "interaction_rules",
    "risk_terms": "risk_terms",
    "crisis_response": "crisis_response",
    "medium_terms": "medium_terms",
    "medium_response": "medium_response",
    "fallback_response": "fallback_response",
    "temperature": "temperature",
    "top_p": "top_p",
    "max_tokens": "max_tokens",
    "max_tokens_user": "max_tokens_user",
    "daily_message_limit": "daily_message_limit",
    "actualizado_por": "actualizado_por",
}


class ChatbotConfigRepository:
    def get_config(self):
        with db_session() as session:
            config = session.get(ChatbotConfig, 1)
            return config.to_dict() if config else None

    def save_config(self, data, admin_id):
        with db_session() as session:
            config = session.get(ChatbotConfig, 1)
            if not config:
                config = ChatbotConfig(id=1)
                session.add(config)
            for data_key, column in CONFIG_COLUMNS.items():
                if data_key == "actualizado_por":
                    setattr(config, column, admin_id)
                elif data_key in data:
                    setattr(config, column, data[data_key])
            config.fecha_actualizacion = datetime.utcnow()
            return 1

    def save_risk_terms_only(self, risk_terms_str, admin_id):
        with db_session() as session:
            config = session.get(ChatbotConfig, 1)
            if not config:
                config = ChatbotConfig(id=1)
                session.add(config)
            config.risk_terms = risk_terms_str
            config.actualizado_por = admin_id
            return 1

    def clear_risk_terms(self, admin_id):
        with db_session() as session:
            config = session.get(ChatbotConfig, 1)
            if config:
                config.risk_terms = ""
                return 1
            return 0

    def get_historial_palabras_riesgo(self):
        with db_session() as session:
            rows = session.execute(
                text("""
                    SELECT nombre, palabrasRiesgoDetectadas, nivelEmocionalDetectado
                    FROM vistahistorialchatbot
                    WHERE palabrasRiesgoDetectadas IS NOT NULL
                      AND palabrasRiesgoDetectadas != ''
                """)
            ).mappings().all()
            return [dict(r) for r in rows]
