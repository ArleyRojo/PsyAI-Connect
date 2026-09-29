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

    # ── Anamnesis ─────────────────────────────────────────────────────────────

    CAMPOS_OBLIGATORIOS_ANAMNESIS = [
        "fechaNacimiento",
        "telefonoPrincipal",
        "direccionResidencia",
        "nivelEscolar",
        "motivoConsulta",
    ]

    def _validar_obligatorios_anamnesis(self, data):
        """Retorna lista de campos obligatorios faltantes."""
        return [c for c in self.CAMPOS_OBLIGATORIOS_ANAMNESIS if not data.get(c)]

    def get_anamnesis(self, paciente_id, profesional_id):
        anamnesis = self.repo.get_anamnesis_by_paciente(paciente_id)
        if not anamnesis:
            return {"success": False, "message": "Anamnesis no encontrada"}, 404
        if anamnesis.idProfesional_id != profesional_id:
            return {"success": False, "message": "No autorizado para ver esta anamnesis"}, 403
        return {"success": True, "anamnesis": anamnesis.to_dict(include_familiares=True)}, 200

    def registrar_anamnesis(self, paciente_id, profesional_id, data):
        from apps.authentication.models import Register

        # Verificar que el paciente existe y tiene rol correcto
        try:
            paciente = Register.objects.get(idUsuario=paciente_id)
        except Register.DoesNotExist:
            return {"success": False, "message": "El paciente no existe"}, 400
        if paciente.rol != "paciente":
            return {"success": False, "message": "El usuario no tiene rol de paciente"}, 400

        # 409 si ya existe
        if self.repo.existe_anamnesis(paciente_id):
            return {"success": False, "message": "Ya existe una anamnesis para este paciente"}, 409

        # Validar obligatorios
        faltantes = self._validar_obligatorios_anamnesis(data)
        if faltantes:
            return {
                "success": False,
                "message": f"Campos obligatorios faltantes: {', '.join(faltantes)}",
            }, 400

        familiares_data = data.pop("familiares", None)
        anamnesis = self.repo.create_anamnesis(paciente_id, profesional_id, data, familiares_data)
        return {"success": True, "anamnesis": anamnesis.to_dict(include_familiares=True)}, 201

    def actualizar_anamnesis(self, paciente_id, profesional_id, data):
        anamnesis = self.repo.get_anamnesis_by_paciente(paciente_id)
        if not anamnesis:
            return {"success": False, "message": "Anamnesis no encontrada"}, 404
        if anamnesis.idProfesional_id != profesional_id:
            return {"success": False, "message": "No autorizado para editar esta anamnesis"}, 403

        # Si vienen familiares se reemplazan completos
        familiares_data = data.pop("familiares", None)
        anamnesis = self.repo.update_anamnesis(anamnesis, data)
        if familiares_data is not None:
            self.repo.replace_familiares(anamnesis, familiares_data)

        # Re-fetch con familiares
        anamnesis = self.repo.get_anamnesis_by_paciente(paciente_id)
        return {"success": True, "anamnesis": anamnesis.to_dict(include_familiares=True)}, 200

    def eliminar_anamnesis(self, paciente_id, profesional_id):
        anamnesis = self.repo.get_anamnesis_by_paciente(paciente_id)
        if not anamnesis:
            return {"success": False, "message": "Anamnesis no encontrada"}, 404
        if anamnesis.idProfesional_id != profesional_id:
            return {"success": False, "message": "No autorizado para eliminar esta anamnesis"}, 403
        anamnesis.delete()
        return {"success": True, "message": "Anamnesis eliminada correctamente"}, 200

    @staticmethod
    def calcular_edad(fecha_nacimiento):
        """Calcula edad a partir de una fecha (date o string YYYY-MM-DD)."""
        import datetime
        if not fecha_nacimiento:
            return None
        if isinstance(fecha_nacimiento, str):
            try:
                fecha_nacimiento = datetime.date.fromisoformat(fecha_nacimiento)
            except ValueError:
                return None
        hoy = datetime.date.today()
        cumple = fecha_nacimiento.replace(year=hoy.year)
        anios = hoy.year - fecha_nacimiento.year
        if cumple > hoy:
            anios -= 1
        return anios

