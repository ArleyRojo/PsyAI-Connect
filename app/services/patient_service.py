import os

from flask import current_app

from app.repositories.patient_repository import PatientRepository
from app.utils.upload_validation import UploadValidator
from app.schemas.patient_schemas import PatientProfileSchema, ChatbotConsentSchema, EvolutionSchema, ChatbotSurveySchema
from app.schemas.base import SchemaValidationError


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
        try:
            validated = PatientProfileSchema.load(data)
        except SchemaValidationError as e:
            first_error = next(iter(e.errors.values()))
            return {"success": False, "message": first_error}, 400
        self.repo.update_patient_profile(validated)
        return {"success": True, "message": "Perfil actualizado"}, 200

    def get_chatbot_consent(self, user_id):
        consent = self.repo.get_chatbot_consent(user_id)
        return {"success": True, "consentimiento_chatbot": consent}, 200

    def update_chatbot_consent(self, user_id, consent):
        try:
            validated = ChatbotConsentSchema.load({"consentimiento_chatbot": consent})
        except SchemaValidationError as e:
            first_error = next(iter(e.errors.values()))
            return {"success": False, "message": first_error}, 400
        consent_value = validated["consentimiento_chatbot"]
        self.repo.update_chatbot_consent(user_id, consent_value)
        return {"success": True, "consentimiento_chatbot": consent_value}, 200

    def save_chatbot_survey(self, user_id, data):
        try:
            validated = ChatbotSurveySchema.load(data)
        except SchemaValidationError as e:
            first_error = next(iter(e.errors.values()))
            return {"success": False, "message": first_error}, 400
        self.repo.save_chatbot_survey(user_id, validated)
        return {"success": True, "message": "Encuesta guardada correctamente"}, 200

    def save_evolution(self, user_id, data):
        try:
            validated = EvolutionSchema.load(data)
        except SchemaValidationError as e:
            first_error = next(iter(e.errors.values()))
            return {"success": False, "message": first_error}, 400
        self.repo.create_patient_evolution(user_id, validated)
        return {"success": True, "message": "Evolución guardada correctamente"}, 200

    def get_evolution_history(self, user_id):
        return {"success": True, "historial": self.repo.get_patient_evolution_history(user_id)}, 200

    def list_patients(self, page=1, limit=20):
        return {"success": True, "pacientes": self.repo.list_patients(page, limit)}, 200

    def list_professionals(self):
        return {"success": True, "profesionales": self.repo.list_professionals()}, 200

    def update_profile_photo(self, user_id, file):
        safe_name, error = UploadValidator.validate(
            file,
            allowed_extensions={"jpg", "jpeg", "png", "gif", "webp"},
        )
        if error:
            return {"success": False, "message": error}, 400

        upload_dir = os.path.join(current_app.root_path, "static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        file.save(os.path.join(upload_dir, safe_name))
        self.repo.update_profile_photo(safe_name, user_id)

        return {
            "success": True,
            "message": "Foto de perfil actualizada",
            "fotoPerfil": safe_name,
        }, 200



