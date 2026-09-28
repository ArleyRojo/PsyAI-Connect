import os
import uuid

from django.conf import settings

from apps.core.utils import validate_file_upload
from apps.patients.repositories import PatientRepository

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


class PatientService:
    def __init__(self):
        self.repo = PatientRepository()

    def get_patient_profile(self, user_id):
        perfil = self.repo.get_patient_profile(user_id)
        if not perfil:
            return {"success": False, "message": "Perfil no encontrado"}, 404
        if perfil.get("fechaRegistro"):
            perfil["fechaRegistro"] = perfil["fechaRegistro"].strftime("%d/%m/%Y")
        return {"success": True, "perfil": perfil}, 200

    def update_patient_profile(self, data):
        numero = data.get("numeroTelefonico")
        if numero is None:
            return {"success": False, "message": "numeroTelefonico es requerido"}, 400
        self.repo.update_patient_profile(data)
        return {"success": True, "message": "Perfil actualizado"}, 200

    def get_preferences(self, user_id):
        prefs = self.repo.get_preferences(user_id)
        return {"success": True, "preferencias": prefs}, 200

    def save_preferences(self, user_id, data):
        # validation is done in serializer
        self.repo.save_preferences(user_id, data)
        return {"success": True, "message": "Preferencias guardadas"}, 200

    def get_chatbot_consent(self, user_id):
        consent = self.repo.get_chatbot_consent(user_id)
        return {"success": True, "consentimiento_chatbot": consent}, 200

    def update_chatbot_consent(self, user_id, consent):
        consent_value = bool(consent)
        self.repo.update_chatbot_consent(user_id, consent_value)
        return {"success": True, "consentimiento_chatbot": consent_value}, 200

    def save_chatbot_survey(self, user_id, data):
        required = ("utilidad", "claridad", "recomendaria")
        missing = [f for f in required if f not in data]
        if missing:
            return {"success": False, "message": f"Faltan campos: {', '.join(missing)}"}, 400
        self.repo.save_chatbot_survey(user_id, data)
        return {"success": True, "message": "Encuesta guardada correctamente"}, 200

    def save_evolution(self, user_id, data):
        self.repo.create_patient_evolution(user_id, data)
        return {"success": True, "message": "Evolución guardada correctamente"}, 200

    def get_evolution_history(self, user_id):
        return {"success": True, "historial": self.repo.get_patient_evolution_history(user_id)}, 200

    def list_patients(self, page=1, limit=20):
        return {"success": True, "pacientes": self.repo.list_patients(page, limit)}, 200

    def list_professionals(self):
        return {"success": True, "profesionales": self.repo.list_professionals()}, 200

    def update_profile_photo(self, user_id, file):
        if not file:
            return {"success": False, "message": "No se envió ningún archivo"}, 400

        name, error = validate_file_upload(file, allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
        if error:
            return {"success": False, "message": error}, 400

        ext = file.name.rsplit(".", 1)[1].lower() if "." in file.name else ""

        safe_name = f"{uuid.uuid4().hex}.{ext}"
        upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        with open(os.path.join(upload_dir, safe_name), "wb+") as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        self.repo.update_profile_photo(safe_name, user_id)
        return {
            "success": True,
            "message": "Foto de perfil actualizada",
            "fotoPerfil": safe_name,
        }, 200
