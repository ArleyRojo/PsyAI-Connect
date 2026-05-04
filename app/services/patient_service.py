import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

from app.repositories import patient_repository

ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def get_patient_profile(user_id):
    perfil = patient_repository.get_patient_profile(user_id)
    if not perfil:
        return {"success": False, "message": "Perfil no encontrado"}, 404
    if perfil.get("fechaRegistro"):
        perfil["fechaRegistro"] = perfil["fechaRegistro"].strftime("%d/%m/%Y")
    return {"success": True, "perfil": perfil}, 200


def update_patient_profile(data):
    patient_repository.update_patient_profile(data)
    return {"success": True, "message": "Perfil actualizado"}, 200


def get_chatbot_consent(user_id):
    consent = patient_repository.get_chatbot_consent(user_id)
    return {"success": True, "consentimiento_chatbot": consent}, 200


def update_chatbot_consent(user_id, consent):
    patient_repository.update_chatbot_consent(user_id, consent)
    return {"success": True, "consentimiento_chatbot": consent}, 200


def save_chatbot_survey(user_id, data):
    patient_repository.save_chatbot_survey(user_id, data)
    return {"success": True, "message": "Encuesta guardada correctamente"}, 200


def save_evolution(user_id, data):
    patient_repository.create_patient_evolution(user_id, data)
    return {"success": True, "message": "Evolución guardada correctamente"}, 200


def get_evolution_history(user_id):
    return {"success": True, "historial": patient_repository.get_patient_evolution_history(user_id)}, 200


def list_patients(page=1, limit=20):
    return {"success": True, "pacientes": patient_repository.list_patients(page, limit)}, 200


def list_professionals():
    return {"success": True, "profesionales": patient_repository.list_professionals()}, 200


def update_profile_photo(user_id, file):
    if not file or not file.filename:
        return {"success": False, "message": "Archivo requerido"}, 400

    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    if extension not in ALLOWED_PHOTO_EXTENSIONS:
        return {"success": False, "message": "Formato de imagen no permitido"}, 400

    upload_dir = os.path.join(current_app.root_path, "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex}.{extension}"
    file.save(os.path.join(upload_dir, unique_filename))
    patient_repository.update_profile_photo(unique_filename, user_id)

    return {
        "success": True,
        "message": "Foto de perfil actualizada",
        "fotoPerfil": unique_filename,
    }, 200
