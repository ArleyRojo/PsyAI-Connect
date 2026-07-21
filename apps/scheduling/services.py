import logging
from datetime import date, datetime, timedelta

from django.utils import timezone as tz

from apps.scheduling.repositories import AppointmentRepository

logger = logging.getLogger(__name__)

VALID_CITAS_ESTADOS = {"Pendiente", "Completada", "Cancelada"}


class AppointmentService:
    def __init__(self):
        self.repo = AppointmentRepository()

    def create_appointment(self, patient_id, data, *, created_by_professional=False):
        professional_id = data.get("idProfesional")
        fecha = data.get("fecha")
        hora = data.get("hora")
        motivo = data.get("motivo", "")
        tipo_cita = data.get("tipoCita")

        if not professional_id or not fecha or not hora:
            return {"success": False, "message": "Datos incompletos"}, 400

        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
            hora_obj = datetime.strptime(hora, "%H:%M").time() if isinstance(hora, str) else hora
            fecha_hora_cita = tz.make_aware(datetime.combine(fecha_obj, hora_obj))
            if fecha_hora_cita < tz.now():
                return {"success": False, "message": "No se pueden agendar citas en el pasado"}, 400
        except (ValueError, TypeError):
            pass

        if created_by_professional:
            target_patient_id = data.get("idPaciente")
            if not target_patient_id:
                return {"success": False, "message": "El campo idPaciente es requerido"}, 400
        else:
            target_patient_id = patient_id
            if not target_patient_id:
                return {"success": False, "message": "Sesión de usuario inválida"}, 401
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
                cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y") if hasattr(cita["fecha"], "strftime") else str(cita["fecha"])
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
        cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y") if hasattr(cita["fecha"], "strftime") else str(cita["fecha"])
        cita["hora"] = str(cita["hora"])
        return {"success": True, "cita": cita}, 200

    def update_status(self, appointment_id, estado, acting_professional_id):
        if not appointment_id or not estado:
            return {"success": False, "message": "Datos incompletos"}, 400

        if estado not in VALID_CITAS_ESTADOS:
            return {"success": False, "message": f"Estado inválido. Opciones: {', '.join(VALID_CITAS_ESTADOS)}"}, 400

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
                cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y") if hasattr(cita["fecha"], "strftime") else str(cita["fecha"])
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
                user_id=professional_id, rol="profesional",
                titulo="Cita cancelada por paciente",
                mensaje=f"El paciente ha cancelado su cita. Motivo: {motivo_cancelacion.strip()}",
                tipo="Alerta",
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
                user_id=patient_id, rol="paciente",
                titulo="Cita cancelada",
                mensaje=f"El profesional ha cancelado tu cita. Motivo: {motivo_cancelacion.strip()}",
                tipo="Alerta",
            )
        return {"success": True, "message": "Cita cancelada correctamente"}, 200

    def get_available_dates(self, professional_id, anio, mes):
        if not professional_id or not anio or not mes:
            return {"success": False, "message": "Datos incompletos"}, 400

        try:
            anio = int(anio)
            mes = int(mes)
        except (ValueError, TypeError):
            return {"success": False, "message": "Año o mes inválido"}, 400

        disponibilidades = self.repo.get_month_availability(professional_id, anio, mes)
        if not disponibilidades:
            return {"success": True, "fechas": []}, 200

        slots_por_fecha = {}
        for disponibilidad in disponibilidades:
            fecha_obj = disponibilidad["fecha"]
            fecha_str = fecha_obj.strftime("%Y-%m-%d") if hasattr(fecha_obj, "strftime") else str(fecha_obj)
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


class DisponibilidadService:
    def __init__(self):
        self.repo = AppointmentRepository()

    def create_availability(self, professional_id, data):
        fecha = data.get("fecha")
        hora_inicio = data.get("horaInicio") or data.get("hora_inicio")
        hora_fin = data.get("horaFin") or data.get("hora_fin")

        if not all([fecha, hora_inicio, hora_fin]):
            return {"success": False, "message": "Datos incompletos (fecha, horaInicio, horaFin)"}, 400

        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
            if fecha_obj < tz.localdate():
                return {"success": False, "message": "No se puede crear disponibilidad en el pasado"}, 400
        except (ValueError, TypeError):
            pass

        try:
            disp = self.repo.create_disponibilidad(
                professional_id, fecha, hora_inicio, hora_fin,
            )
            return {"success": True, "message": "Disponibilidad creada", "disponibilidad": disp}, 201
        except Exception as e:
            logger.error(f"Error creating disponibilidad: {e}")
            return {"success": False, "message": "Error al crear disponibilidad"}, 500

    def get_availability(self, professional_id):
        rows = self.repo.get_all_disponibilidad(professional_id)
        disponibilidad = [
            {
                "idDisponibilidad": r[0],
                "fecha": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
                "hora_inicio": r[2].strftime("%H:%M") if hasattr(r[2], "strftime") else str(r[2]),
                "hora_fin": r[3].strftime("%H:%M") if hasattr(r[3], "strftime") else str(r[3]),
                "estado": r[4],
            }
            for r in rows
        ]
        return {"success": True, "disponibilidad": disponibilidad}, 200
