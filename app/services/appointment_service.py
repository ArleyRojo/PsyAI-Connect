from datetime import date, datetime, timedelta

from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.admin_repository import AdminRepository
from app.schemas.appointment_schemas import CreateCitaSchema, UpdateCitaSchema
from app.schemas.base import SchemaValidationError


class AppointmentService:
    def __init__(self):
        self.repo = AppointmentRepository()

    def create_appointment(self, patient_id, data, *, created_by_professional=False):
        try:
            validated = CreateCitaSchema.load(data)
        except SchemaValidationError as e:
            first_error = next(iter(e.errors.values()))
            return {"success": False, "message": first_error}, 400

        professional_id = validated["idProfesional"]
        fecha = validated["fecha"]
        hora = validated["hora"]
        motivo = validated["motivo"]
        tipo_cita = data.get("tipoCita")

        target_patient_id = data.get("idPaciente") if created_by_professional else patient_id
        existing = self.repo.get_appointment_in_slot(professional_id, fecha, hora)
        if existing:
            if existing["idPaciente"] == target_patient_id:
                self.repo.cancel_patient_appointment(
                    existing["idCita"], target_patient_id,
                    "Reemplazada por nuevo intento de agendamiento"
                )
            else:
                msg = "Ese horario ya está ocupado" if created_by_professional else "Horario no disponible"
                return {"success": False, "message": msg}, 409

        cita_id = self.repo.create_appointment(
            target_patient_id, professional_id, fecha, hora, tipo_cita, motivo,
            created_by_professional if created_by_professional else False,
        )
        return {"success": True, "message": "Cita agendada correctamente", "idCita": cita_id}, 200

    def get_available_times(self, professional_id, fecha):
        if not professional_id or not fecha:
            return {"success": False, "message": "Datos incompletos"}, 400

        disponibilidades = self.repo.get_daily_availability(professional_id, fecha)
        if not disponibilidades:
            return {"success": True, "horarios": []}, 200

        ocupadas = self.repo.get_taken_times(professional_id, fecha)
        horarios_set = set()

        for disponibilidad in disponibilidades:
            inicio = disponibilidad["hora_inicio"]
            fin = disponibilidad["hora_fin"]
            if isinstance(inicio, timedelta):
                inicio = (datetime.min + inicio).time()
            if isinstance(fin, timedelta):
                fin = (datetime.min + fin).time()

            hora_actual = inicio
            while hora_actual < fin:
                h_str = hora_actual.strftime("%H:%M")
                if h_str not in ocupadas:
                    horarios_set.add(h_str)
                hora_actual = (datetime.combine(date.today(), hora_actual) + timedelta(minutes=30)).time()

        horarios_ordenados = sorted(list(horarios_set))
        return {"success": True, "horarios": horarios_ordenados}, 200

    def list_professional_appointments(self, professional_id, *, pending_only=False, page=1, limit=20):
        citas = self.repo.get_professional_appointments(
            professional_id, pending_only=pending_only, page=page, limit=limit,
        )
        for cita in citas:
            if cita.get("fecha"):
                cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y")
            if cita.get("hora"):
                cita["hora"] = str(cita["hora"])
            if cita.get("fotoPerfil"):
                cita["foto_perfil"] = cita["fotoPerfil"]
        return {"success": True, "citas": citas}, 200

    def get_taken_slots(self, professional_id, fecha):
        if not professional_id or not fecha:
            return {"success": False, "message": "Datos incompletos"}, 400
        return {
            "success": True,
            "horarios_ocupados": self.repo.get_taken_times_by_professional(professional_id, fecha),
        }, 200

    def get_next_patient_appointment(self, patient_id):
        cita = self.repo.get_next_patient_appointment(patient_id)
        if not cita:
            return {"success": True, "cita": None}, 200
        cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y")
        cita["hora"] = str(cita["hora"])
        return {"success": True, "cita": cita}, 200

    def update_status(self, appointment_id, estado, acting_professional_id):
        if not appointment_id or not estado:
            return {"success": False, "message": "Datos incompletos"}, 400
        try:
            validated = UpdateCitaSchema.load({"estado": estado})
        except SchemaValidationError as e:
            first_error = next(iter(e.errors.values()))
            return {"success": False, "message": first_error}, 400
        estado = validated["estado"]

        row = self.repo.get_appointment_owner(appointment_id)
        if not row:
            return {"success": False, "message": "Cita no encontrada"}, 404
        if row[0] != acting_professional_id:
            return {"success": False, "message": "No tienes permiso"}, 403

        self.repo.update_appointment_status(appointment_id, estado)
        return {"success": True, "message": f"Cita {estado}"}, 200

    def list_patient_appointments(self, patient_id):
        citas = self.repo.get_patient_appointments(patient_id)
        for cita in citas:
            if cita.get("fecha"):
                cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y")
            if cita.get("hora"):
                cita["hora"] = str(cita["hora"])
        return {"success": True, "citas": citas}, 200

    def cancel_appointment(self, appointment_id, patient_id, motivo_cancelacion):
        if not motivo_cancelacion or not motivo_cancelacion.strip():
            return {"success": False, "message": "Debes indicar el motivo de la cancelación"}, 400

        row = self.repo.get_appointment_owner(appointment_id)
        if not row:
            return {"success": False, "message": "Cita no encontrada"}, 404

        professional_id = row[0]
        rowcount = self.repo.cancel_patient_appointment(appointment_id, patient_id, motivo_cancelacion.strip())
        if rowcount == 0:
            return {"success": False, "message": "Cita no encontrada o ya cancelada"}, 404

        if professional_id:
            self.repo.create_notification(
                user_id=professional_id, rol='profesional',
                titulo="Cita cancelada por paciente",
                mensaje=f"El paciente ha cancelado su cita. Motivo: {motivo_cancelacion.strip()}",
                tipo="Alerta"
            )
        return {"success": True, "message": "Cita cancelada correctamente"}, 200

    def cancel_professional_appointment(self, appointment_id, professional_id, motivo_cancelacion):
        if not motivo_cancelacion or not motivo_cancelacion.strip():
            return {"success": False, "message": "Debes indicar el motivo de la cancelación"}, 400

        row = self.repo.get_appointment_owner(appointment_id)
        if not row:
            return {"success": False, "message": "Cita no encontrada"}, 404
        if row[0] != professional_id:
            return {"success": False, "message": "No tienes permiso para cancelar esta cita"}, 403

        rowcount = self.repo.cancel_professional_appointment(
            appointment_id, professional_id, motivo_cancelacion.strip()
        )
        if rowcount == 0:
            return {"success": False, "message": "No se pudo cancelar la cita"}, 400

        patient_id = row[1] if len(row) > 1 else None
        if patient_id:
            self.repo.create_notification(
                user_id=patient_id, rol='paciente',
                titulo="Cita cancelada",
                mensaje=f"El profesional ha cancelado tu cita. Motivo: {motivo_cancelacion.strip()}",
                tipo="Alerta"
            )
        return {"success": True, "message": "Cita cancelada correctamente"}, 200

    def get_available_dates(self, professional_id, anio, mes):
        if not professional_id or not anio or not mes:
            return {"success": False, "message": "Datos incompletos"}, 400

        disponibilidades = self.repo.get_month_availability(professional_id, anio, mes)
        if not disponibilidades:
            return {"success": True, "fechas": []}, 200

        slots_por_fecha = {}
        for disponibilidad in disponibilidades:
            fecha_str = disponibilidad["fecha"].strftime("%Y-%m-%d")
            inicio = disponibilidad["hora_inicio"]
            fin = disponibilidad["hora_fin"]
            if isinstance(inicio, timedelta):
                inicio = (datetime.min + inicio).time()
            if isinstance(fin, timedelta):
                fin = (datetime.min + fin).time()
            slots_por_fecha.setdefault(fecha_str, 0)
            hora_actual = inicio
            while hora_actual < fin:
                slots_por_fecha[fecha_str] += 1
                hora_actual = (datetime.combine(date.today(), hora_actual) + timedelta(minutes=30)).time()

        ocupadas_por_fecha = self.repo.get_month_taken_counts(professional_id, anio, mes)
        fechas = [
            fecha_key
            for fecha_key, total_slots in slots_por_fecha.items()
            if ocupadas_por_fecha.get(fecha_key, 0) < total_slots
        ]
        return {"success": True, "fechas": sorted(fechas)}, 200
