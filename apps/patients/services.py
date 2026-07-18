import os
import uuid

from django.conf import settings

from apps.patients.repositories import PatientRepository

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAGIC_BYTES = {
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89\x50\x4e\x47",),
    "gif": (b"\x47\x49\x46\x38",),
    "webp": (b"\x52\x49\x46\x46",),
}


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

        filename = file.name
        ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return {"success": False, "message": f"Extensión .{ext} no permitida"}, 400

        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file.size > max_size:
            return {
                "success": False,
                "message": f"El archivo supera los {settings.MAX_UPLOAD_SIZE_MB} MB",
            }, 400

        raw = file.read(4096)
        file.seek(0)
        expected = MAGIC_BYTES.get(ext)
        if expected and not any(raw.startswith(sig) for sig in expected):
            return {
                "success": False,
                "message": "El archivo no coincide con el formato esperado (magic bytes inválidos)",
            }, 400

        safe_name = f"{uuid.uuid4().hex}.{ext}"
        upload_dir = os.path.join(settings.STATICFILES_DIRS[0], "uploads")
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
