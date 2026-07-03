import json
from app.repositories.chatbot_config_repository import ChatbotConfigRepository
from app.services.chatbot_config_events import publish_config_update


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
                    "fallback_response": "",
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500,
                    "max_tokens_user": 1000,
                    "daily_message_limit": 20,
                    "fecha_actualizacion": None,
                    "actualizado_por": None,
                },
            }, 200
        return {"success": True, "config": config}, 200

    def save_config(self, data, admin_id):
        self.repo.save_config(data, admin_id)
        nueva_config = self.repo.get_config()
        publish_config_update(nueva_config)
        return {"success": True, "message": "Configuración guardada correctamente"}, 200

    def save_risk_terms(self, risk_terms_str, admin_id):
        self.repo.save_risk_terms_only(risk_terms_str, admin_id)
        config = self.repo.get_config()
        publish_config_update(config)
        return {"success": True, "message": "Términos de riesgo guardados"}, 200

    def clear_risk_terms(self, admin_id):
        self.repo.clear_risk_terms(admin_id)
        publish_config_update({"risk_terms": "[]"})
        return {"success": True, "message": "Términos de riesgo eliminados"}, 200

    def get_historial_palabras_riesgo(self):
        rows = self.repo.get_historial_palabras_riesgo()
        return {"success": True, "historial": rows}, 200



