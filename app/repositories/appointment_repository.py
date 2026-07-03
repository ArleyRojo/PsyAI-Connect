from datetime import timedelta, date
from sqlalchemy import select, func
from app.database.session import db_session
from app.models.citas import Citas
from app.models.disponibilidad import Disponibilidad
from app.models.notificaciones import Notificaciones
from app.models.register import Register
from app.models.facturas import Facturas


class AppointmentRepository:
    @staticmethod
    def _format_time(value):
        if value is None:
            return None
        if isinstance(value, timedelta):
            total_seconds = int(value.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}"
        elif hasattr(value, 'strftime'):
            return value.strftime("%H:%M")
        elif isinstance(value, str):
            return value[:5] if len(value) >= 5 else value
        return str(value)

    def appointment_exists(self, professional_id, fecha, hora):
        with db_session() as session:
            stmt = select(Citas.idCita).where(
                Citas.idProfesional == professional_id,
                Citas.fecha == fecha,
                Citas.hora == hora,
                Citas.estado != "Cancelada",
            )
            return session.execute(stmt).scalar_one_or_none() is not None

    def get_appointment_in_slot(self, professional_id, fecha, hora):
        with db_session() as session:
            stmt = select(Citas.idCita, Citas.idPaciente).where(
                Citas.idProfesional == professional_id,
                Citas.fecha == fecha,
                Citas.hora == hora,
                Citas.estado != "Cancelada",
            )
            row = session.execute(stmt).one_or_none()
            if row:
                return {"idCita": row[0], "idPaciente": row[1]}
            return None

    def create_appointment(self, patient_id, professional_id, fecha, hora, tipo_cita, motivo, creado_por_profesional=False):
        with db_session() as session:
            cita = Citas(
                idPaciente=patient_id,
                idProfesional=professional_id,
                fecha=fecha,
                hora=hora,
                tipoCita=tipo_cita,
                motivo=motivo,
                estado="Pendiente",
                creado_por_profesional=creado_por_profesional,
            )
            session.add(cita)
            session.flush()
            from app.repositories.admin_repository import AdminRepository
            AdminRepository.increment_logs_version()
            return cita.idCita

    def get_daily_availability(self, professional_id, fecha):
        with db_session() as session:
            stmt = select(Disponibilidad.hora_inicio, Disponibilidad.hora_fin).where(
                Disponibilidad.idProfesional == professional_id,
                func.date(Disponibilidad.fecha) == fecha,
                Disponibilidad.estado == "Disponible",
            )
            rows = session.execute(stmt).all()
            return [{"hora_inicio": r[0], "hora_fin": r[1]} for r in rows]

    def get_taken_times(self, professional_id, fecha):
        with db_session() as session:
            stmt = select(Citas.hora).where(
                Citas.idProfesional == professional_id,
                Citas.fecha == fecha,
                Citas.estado != "Cancelada",
            )
            rows = session.execute(stmt).all()
            return [AppointmentRepository._format_time(r[0]) for r in rows]

    def get_professional_appointments(self, professional_id, *, pending_only=False, page=1, limit=20):
        offset = (page - 1) * limit
        with db_session() as session:
            stmt = select(
                Citas.idCita, Register.nombre.label("paciente"),
                Register.fotoPerfil, Citas.fecha, Citas.hora,
                Citas.tipoCita, Citas.motivo, Citas.estado,
                Citas.creado_por_profesional,
            ).join(Register, Citas.idPaciente == Register.idUsuario).where(
                Citas.idProfesional == professional_id
            )
            if pending_only:
                stmt = stmt.where(Citas.estado == "Pendiente")
            else:
                stmt = stmt.where(Citas.estado != "Cancelada")
                stmt = stmt.where(Citas.fecha >= date.today())
            stmt = stmt.order_by(Citas.fecha.asc(), Citas.hora.asc()).limit(limit).offset(offset)
            rows = session.execute(stmt).all()
            result = []
            for r in rows:
                d = {
                    "idCita": r[0], "paciente": r[1], "fotoPerfil": r[2],
                    "fecha": r[3], "hora": AppointmentRepository._format_time(r[4]),
                    "tipoCita": r[5], "motivo": r[6], "estado": r[7],
                    "creado_por_profesional": r[8],
                }
                result.append(d)
            return result

    def get_taken_times_by_professional(self, professional_id, fecha):
        with db_session() as session:
            stmt = select(Citas.hora).where(
                Citas.idProfesional == professional_id,
                Citas.fecha == fecha,
                Citas.estado != "Cancelada",
            )
            rows = session.execute(stmt).all()
            return [AppointmentRepository._format_time(r[0]) for r in rows]

    def get_next_patient_appointment(self, patient_id):
        with db_session() as session:
            stmt = select(
                Citas.fecha, Citas.hora, Citas.tipoCita,
                Register.nombre.label("profesional"),
            ).join(Register, Citas.idProfesional == Register.idUsuario).where(
                Citas.idPaciente == patient_id,
                Citas.estado == "Pendiente",
                Citas.fecha >= date.today(),
            ).order_by(Citas.fecha.asc(), Citas.hora.asc()).limit(1)
            row = session.execute(stmt).one_or_none()
            if row:
                return {
                    "fecha": row[0],
                    "hora": AppointmentRepository._format_time(row[1]),
                    "tipoCita": row[2],
                    "profesional": row[3],
                }
            return None

    def get_appointment_owner(self, appointment_id):
        with db_session() as session:
            cita = session.get(Citas, appointment_id)
            if cita:
                return (cita.idProfesional, cita.idPaciente)
            return None

    def update_appointment_status(self, appointment_id, estado):
        with db_session() as session:
            cita = session.get(Citas, appointment_id)
            if cita:
                cita.estado = estado

    def get_patient_appointments(self, patient_id):
        with db_session() as session:
            stmt = select(
                Citas.idCita, Citas.fecha, Citas.hora, Citas.tipoCita,
                Citas.motivo, Citas.estado, Citas.motivoCancelacion,
                Register.nombre.label("profesional"),
                Citas.creado_por_profesional,
                Facturas.estadoPago, Facturas.idFactura,
            ).join(Register, Citas.idProfesional == Register.idUsuario).outerjoin(
                Facturas, Citas.idCita == Facturas.idCita
            ).where(Citas.idPaciente == patient_id).order_by(
                Citas.fecha.desc(), Citas.hora.desc()
            )
            rows = session.execute(stmt).all()
            result = []
            for r in rows:
                d = {
                    "idCita": r[0], "fecha": r[1], "hora": AppointmentRepository._format_time(r[2]),
                    "tipoCita": r[3], "motivo": r[4], "estado": r[5],
                    "motivoCancelacion": r[6], "profesional": r[7],
                    "creado_por_profesional": r[8], "estadoPago": r[9],
                    "idFactura": r[10],
                }
                result.append(d)
            return result

    def cancel_patient_appointment(self, appointment_id, patient_id, motivo_cancelacion):
        with db_session() as session:
            cita = session.get(Citas, appointment_id)
            if cita and cita.idPaciente == patient_id:
                cita.estado = "Cancelada"
                cita.motivoCancelacion = motivo_cancelacion
                return 1
            return 0

    def cancel_professional_appointment(self, appointment_id, professional_id, motivo_cancelacion):
        with db_session() as session:
            cita = session.get(Citas, appointment_id)
            if cita and cita.idProfesional == professional_id:
                cita.estado = "Cancelada"
                cita.motivoCancelacion = motivo_cancelacion
                return 1
            return 0

    def create_notification(self, user_id, rol, titulo, mensaje, tipo="Cita"):
        with db_session() as session:
            session.add(Notificaciones(
                idUsuario=user_id, rol=rol, titulo=titulo,
                mensaje=mensaje, tipo=tipo, enviado_por="Sistema", estado="enviado",
            ))
            from app.repositories.admin_repository import AdminRepository
            AdminRepository.increment_logs_version()

    def get_month_availability(self, professional_id, anio, mes):
        with db_session() as session:
            stmt = select(
                Disponibilidad.fecha, Disponibilidad.hora_inicio, Disponibilidad.hora_fin
            ).where(
                Disponibilidad.idProfesional == professional_id,
                func.year(Disponibilidad.fecha) == anio,
                func.month(Disponibilidad.fecha) == mes,
                Disponibilidad.estado == "Disponible",
            )
            rows = session.execute(stmt).all()
            return [{"fecha": r[0], "hora_inicio": r[1], "hora_fin": r[2]} for r in rows]

    def get_month_taken_counts(self, professional_id, anio, mes):
        with db_session() as session:
            rows = session.execute(
                select(
                    func.date_format(Citas.fecha, "%Y-%m-%d").label("fecha"),
                    func.count().label("ocupadas"),
                ).where(
                    Citas.idProfesional == professional_id,
                    func.year(Citas.fecha) == anio,
                    func.month(Citas.fecha) == mes,
                    Citas.estado != "Cancelada",
                ).group_by(Citas.fecha)
            ).all()
            return {r[0]: r[1] for r in rows}
