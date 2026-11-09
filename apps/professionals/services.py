import logging

from apps.professionals.repositories import ProfessionalRepository

logger = logging.getLogger(__name__)

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

    def assign_patient(self, professional_id, patient_id):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        patient_exists, created = self.repo.assign_patient(professional_id, patient_id)
        if not patient_exists:
            return {"success": False, "message": "Paciente no encontrado"}, 404

        try:
            from apps.scheduling.models import Notificaciones
            from apps.scheduling.repositories import AppointmentRepository
            from apps.authentication.models import Register

            appointment_repo = AppointmentRepository()
            paciente = Register.objects.filter(idUsuario=patient_id).first()
            profesional = Register.objects.filter(idUsuario=professional_id).first()
            nombre_paciente = paciente.nombre if paciente else f"Paciente #{patient_id}"
            nombre_profesional = profesional.nombre if profesional else "Tu profesional"

            if created:
                appointment_repo.create_notification(
                    professional_id,
                    "profesional",
                    "Nuevo paciente asignado",
                    f"Se te ha asignado un nuevo paciente: {nombre_paciente}.",
                    "Asignacion",
                )

            if paciente:
                titulo_paciente = "Te asignaron un profesional"
                mensaje_paciente = (
                    f"{nombre_profesional} fue asignado a tu atención. "
                    "Puedes escribirle desde Mensajes."
                )
                ya_notificado = Notificaciones.objects.filter(
                    idUsuario_id=patient_id,
                    rol="paciente",
                    tipo="Asignacion",
                    titulo=titulo_paciente,
                    mensaje=mensaje_paciente,
                ).exists()
                if created or not ya_notificado:
                    appointment_repo.create_notification(
                        patient_id,
                        "paciente",
                        titulo_paciente,
                        mensaje_paciente,
                        "Asignacion",
                    )
        except Exception as e:
            logger.warning(f"Error creando notificación de asignación: {e}")

        return {"success": True, "message": "Paciente asignado correctamente"}, 200

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
        report = self.repo.update_report(professional_id, data)
        if not report:
            return {"success": False, "message": "Reporte no encontrado"}, 404
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

    def get_deleted_reports(self, professional_id, is_admin=False):
        if not is_admin:
            check = self._check_verificacion(professional_id)
            if check:
                return check
        owner_id = None if is_admin else professional_id
        return {"success": True, "reportes": self.repo.get_deleted_reports(owner_id)}, 200

    def list_patients_for_chat(self, professional_id):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        pacientes = self.repo.list_professional_patients(professional_id)
        return {
            "success": True,
            "pacientes": [
                {"idUsuario": p["idUsuario"], "nombre": p["nombre"], "fotoPerfil": p["fotoPerfil"]}
                for p in pacientes
            ],
        }, 200

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
        return {"success": True, "historial": chat_repo.get_history(patient_id)}, 200

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

    # ── Consejos al paciente (HU-54 / HU-68) ──────────────────────────────

    def crear_consejo(self, professional_id, patient_id, data):
        check = self._check_verificacion(professional_id)
        if check:
            return check
        titulo = (data.get("titulo") or "").strip()
        descripcion = (data.get("descripcion") or "").strip()
        if not titulo or not descripcion:
            return {"success": False, "message": "El título y la descripción son obligatorios"}, 400
        asignacion = self.repo.get_assignment(professional_id, patient_id)
        if not asignacion:
            return {"success": False, "message": "No tienes asignado este paciente"}, 403
        consejo = self.repo.create_consejo(asignacion, titulo, descripcion)
        self._avisar_consejo_nuevo(asignacion, titulo)
        return {"success": True, "message": "Consejo enviado al paciente", "consejo": consejo.to_dict()}, 201

    def listar_consejos(self, professional_id, patient_id):
        asignacion = self.repo.get_assignment(professional_id, patient_id)
        if not asignacion:
            return {"success": False, "message": "No tienes asignado este paciente"}, 403
        return {"success": True, "consejos": self.repo.list_consejos_asignacion(asignacion)}, 200

    def eliminar_consejo(self, professional_id, consejo_id):
        consejo = self.repo.get_consejo_profesional(consejo_id, professional_id)
        if not consejo:
            return {"success": False, "message": "Consejo no encontrado"}, 404
        self.repo.delete_consejo(consejo)
        return {"success": True, "message": "Consejo eliminado"}, 200

    def consejos_del_paciente(self, patient_id):
        return {"success": True, "consejos": self.repo.list_consejos_paciente(patient_id)}, 200

    def marcar_consejo(self, patient_id, consejo_id, completado):
        consejo = self.repo.get_consejo_paciente(consejo_id, patient_id)
        if not consejo:
            return {"success": False, "message": "Consejo no encontrado"}, 404
        data = self.repo.set_consejo_completado(consejo, completado)
        mensaje = "Consejo marcado como completado" if completado else "Consejo marcado como pendiente"
        return {"success": True, "message": mensaje, "consejo": data}, 200

    def _avisar_consejo_nuevo(self, asignacion, titulo):
        """Aviso en la campana del paciente y por su canal elegido (correo/WhatsApp)."""
        try:
            from apps.scheduling.repositories import AppointmentRepository
            from apps.core.notifier import notificar_paciente

            profesional = asignacion.idProfesional.nombre
            mensaje = f"{profesional} te envió un consejo: {titulo}. Míralo en Mis consejos."
            AppointmentRepository().create_notification(
                asignacion.idPaciente_id, "paciente", "Nuevo consejo de tu profesional", mensaje, "Consejo"
            )
            notificar_paciente(asignacion.idPaciente, "Nuevo consejo de tu profesional", mensaje, "mensaje_profesional")
        except Exception as e:
            logger.warning(f"Error avisando consejo nuevo: {e}")
