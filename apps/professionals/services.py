from apps.professionals.repositories import ProfessionalRepository

try:
    from apps.chatbot.repositories import ChatRepository
except ImportError:
    ChatRepository = None


class ProfessionalService:
    def __init__(self):
        self.repo = ProfessionalRepository()
        self.chat_repo = ChatRepository() if ChatRepository else None

    def _check_verificacion(self, professional_id):
        """Verifica si el profesional está verificado."""
        perfil = self.repo.get_professional_profile(professional_id)
        if not perfil or not perfil.get("verificado"):
            return {"success": False, "message": "Profesional no verificado. Su cuenta está en proceso de verificación."}, 403
        return None

    def get_profile(self, user_id):
        perfil = self.repo.get_professional_profile(user_id)
        if not perfil:
            return {"success": False, "message": "Perfil no encontrado"}, 404
        if perfil.get("fechaRegistro"):
            perfil["fechaRegistro"] = perfil["fechaRegistro"].strftime("%d/%m/%Y")
        return {"success": True, "perfil": perfil}, 200

    def update_profile(self, data):
        if not data.get("especialidad") and not data.get("tarjetaProfesional") and not data.get("numeroRethus") and not data.get("experiencia"):
            return {"success": False, "message": "No se enviaron datos para actualizar"}, 400
        self.repo.update_professional_profile(data)
        return {"success": True, "message": "Perfil actualizado"}, 200

    def get_dashboard(self, professional_id):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        data = self.repo.get_dashboard_stats(professional_id)
        for actividad in data["actividades"]:
            if actividad.get("fecha"):
                actividad["fecha"] = actividad["fecha"].strftime("%d/%m/%Y")
            if actividad.get("hora"):
                actividad["hora"] = str(actividad["hora"])
        for cita in data.get("proximas_citas", []):
            if cita.get("fecha"):
                cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y")
            if cita.get("hora"):
                cita["hora"] = str(cita["hora"])
        return {"success": True, **data}, 200

    def list_patients(self, professional_id):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        return {"success": True, "pacientes": self.repo.list_professional_patients(professional_id)}, 200

    def save_diagnosis(self, professional_id, data):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        if not data.get("idPaciente"):
            return {"success": False, "message": "idPaciente es requerido"}, 400
        if not self.repo.professional_has_patient(professional_id, data["idPaciente"]):
            return {"success": False, "message": "No tienes asignado este paciente"}, 403
        self.repo.save_diagnosis(professional_id, data)
        return {"success": True, "message": "Diagnóstico guardado correctamente"}, 200

    def diagnosis_history(self, professional_id):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        return {"success": True, "historial": self.repo.get_diagnosis_history(professional_id)}, 200

    def report_overview(self, professional_id):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        data = self.repo.get_report_overview(professional_id)
        return {"success": True, **data}, 200

    def create_report(self, professional_id, data):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        patient_id = data.get("idPaciente")
        if patient_id and not self.repo.professional_has_patient(professional_id, patient_id):
            return {"success": False, "message": "No puedes generar reportes para este paciente"}, 403
        if patient_id and data.get("tipoReporte") == "diagnosticos":
            latest_diagnosis = self.repo.get_latest_patient_diagnosis(professional_id, patient_id)
            if latest_diagnosis:
                data = {**data, **latest_diagnosis}
        self.repo.create_report(professional_id, data)
        return {"success": True, "message": "Reporte generado correctamente"}, 200

    def update_report(self, professional_id, data):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        self.repo.update_report(professional_id, data)
        return {"success": True, "message": "Reporte actualizado correctamente"}, 200

    def delete_report(self, professional_id, report_id):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        self.repo.delete_report(professional_id, report_id)
        return {"success": True, "message": "Reporte eliminado correctamente"}, 200

    def all_evolution(self, professional_id):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        historial = self.repo.get_all_patient_evolution(professional_id)
        riesgo_bajo = []
        from apps.chatbot.repositories import ChatRepository
        chat_repo = ChatRepository()
        if chat_repo:
            riesgo_bajo = chat_repo.get_low_risk_counts_for_professional(professional_id)
        return {
            "success": True,
            "historial": historial,
            "riesgo_bajo_chatbot": riesgo_bajo,
        }, 200

    def all_prediagnosticos(self, professional_id):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        prediagnosticos = []
        from apps.chatbot.repositories import ChatRepository
        chat_repo = ChatRepository()
        if chat_repo:
            prediagnosticos = chat_repo.get_prediagnosticos_for_professional(professional_id)
        return {"success": True, "prediagnosticos": prediagnosticos}, 200

    def get_deleted_reports(self, professional_id):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        return {"success": True, "reportes": self.repo.get_deleted_reports(professional_id)}, 200

    def list_patients_for_chat(self):
        from apps.authentication.models import Register
        return [
            {
                "idUsuario": u.idUsuario,
                "nombre": u.nombre,
                "fotoPerfil": u.fotoPerfil,
                "edad": None,
                "genero": None,
                "contacto": u.email,
            }
            for u in Register.objects.filter(rol="paciente", activo=True, estadoCuenta="Activa").order_by("nombre")
        ]

    def get_patient_chatbot_history(self, professional_id, patient_id):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        if not self.repo.professional_has_patient(professional_id, patient_id):
            return {"success": False, "message": "No tienes acceso al historial de este paciente"}, 403
        from apps.chatbot.repositories import ChatRepository
        chat_repo = ChatRepository()
        if not chat_repo:
            return {"success": False, "message": "Servicio de chatbot no disponible"}, 503
        return {"success": True, "historial": self.chat_repo.get_history(patient_id)}, 200

    # Métodos de verificación
    def verificar_profesional(self, admin_user_id, professional_id):
        """Verifica un profesional (solo admin)."""
        from django.utils import timezone
        from apps.professionals.models import PerfilProfesional
        perfil = PerfilProfesional.objects.filter(idProfesional_id=professional_id).first()
        if not perfil:
            return {"success": False, "message": "Profesional no encontrado"}, 404
        if perfil.verificado:
            return {"success": False, "message": "El profesional ya está verificado"}, 400
        perfil.verificado = True
        perfil.fechaVerificacion = timezone.now()
        perfil.verificadoPor_id = admin_user_id
        perfil.save(update_fields=["verificado", "fechaVerificacion", "verificadoPor"])
        return {"success": True, "message": "Profesional verificado correctamente"}, 200

    def desverificar_profesional(self, admin_user_id, professional_id):
        """Desverifica un profesional (solo admin)."""
        from apps.professionals.models import PerfilProfesional
        perfil = PerfilProfesional.objects.filter(idProfesional_id=professional_id).first()
        if not perfil:
            return {"success": False, "message": "Profesional no encontrado"}, 404
        if not perfil.verificado:
            return {"success": False, "message": "El profesional no está verificado"}, 400
        perfil.verificado = False
        perfil.fechaVerificacion = None
        perfil.verificadoPor = None
        perfil.save(update_fields=["verificado", "fechaVerificacion", "verificadoPor"])
        return {"success": True, "message": "Profesional desverificado correctamente"}, 200