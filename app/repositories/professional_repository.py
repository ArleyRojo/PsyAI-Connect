from datetime import date
from sqlalchemy import select, func, text
from app.database.session import db_session
from app.models.register import Register
from app.models.perfil_profesional import PerfilProfesional
from app.models.perfil_paciente import PerfilPaciente
from app.models.disponibilidad import Disponibilidad
from app.models.citas import Citas
from app.models.evolucion_paciente import EvolucionPaciente
from app.models.pacientes_profesional import PacientesProfesional
from app.models.reportes import Reportes


class ProfessionalRepository:
    def get_professional_profile(self, user_id):
        with db_session() as session:
            user = session.get(Register, user_id)
            if not user:
                return None
            perfil = session.get(PerfilProfesional, user_id)
            return {
                "nombre": user.nombre,
                "email": user.email,
                "fotoPerfil": user.fotoPerfil,
                "fechaRegistro": user.fechaRegistro,
                "especialidad": perfil.especialidad if perfil else None,
                "licencia": perfil.licencia if perfil else None,
                "experiencia": perfil.experiencia if perfil else None,
                "estado": perfil.estado if perfil else None,
                "edad": perfil.edad if perfil else None,
                "genero": perfil.genero if perfil else None,
            }

    def update_professional_profile(self, data):
        with db_session() as session:
            perfil = session.get(PerfilProfesional, data.get("idUsuario"))
            if perfil:
                perfil.especialidad = data.get("especialidad")
                perfil.licencia = data.get("licencia")
                perfil.experiencia = data.get("experiencia")

    def create_availability(self, professional_id, data):
        with db_session() as session:
            session.add(Disponibilidad(
                idProfesional=professional_id,
                fecha=data.get("fecha"),
                hora_inicio=data.get("hora_inicio"),
                hora_fin=data.get("hora_fin"),
                estado="Disponible",
            ))

    def get_availability(self, professional_id):
        with db_session() as session:
            stmt = select(Disponibilidad).where(
                Disponibilidad.idProfesional == professional_id,
                Disponibilidad.estado == "Disponible",
            )
            rows = session.execute(stmt).scalars().all()
            return [r.to_dict() for r in rows]

    def get_dashboard_stats(self, professional_id):
        with db_session() as session:
            stats = session.execute(
                text("""
                    SELECT
                        COUNT(DISTINCT CASE WHEN estado != 'Cancelada' THEN idPaciente END) as pacientes_activos,
                        COUNT(CASE WHEN fecha = CURDATE() AND estado != 'Cancelada' THEN 1 END) as citas_hoy,
                        COUNT(CASE WHEN estado = 'Pendiente' THEN 1 END) as citas_pendientes
                    FROM Citas WHERE idProfesional = :pid
                """),
                {"pid": professional_id}
            ).mappings().one_or_none()
            actividades_rows = session.execute(
                text("""
                    SELECT r.nombre as paciente, c.fecha, c.hora, c.tipoCita, c.estado, c.idCita
                    FROM Citas c JOIN Register r ON c.idPaciente = r.idUsuario
                    WHERE c.idProfesional = :pid AND c.estado != 'Cancelada'
                    ORDER BY c.fecha DESC, c.hora DESC LIMIT 3
                """),
                {"pid": professional_id}
            ).mappings().all()
            actividades = [dict(r) for r in actividades_rows]
            proximas_rows = session.execute(
                text("""
                    SELECT c.idCita, r.nombre as paciente, r.idUsuario as idPaciente, r.fotoPerfil,
                           c.fecha, c.hora, c.tipoCita, c.estado
                    FROM Citas c JOIN Register r ON c.idPaciente = r.idUsuario
                    WHERE c.idProfesional = :pid
                      AND c.estado IN ('Pendiente', 'Confirmada')
                      AND c.fecha >= CURDATE()
                      AND c.fecha <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                    ORDER BY c.fecha ASC, c.hora ASC LIMIT 10
                """),
                {"pid": professional_id}
            ).mappings().all()
            proximas_citas = [dict(r) for r in proximas_rows]
            reportes_data = session.execute(
                text("""
                    SELECT COUNT(*) as total_reportes,
                           SUM(estado = 'Completado') as completados,
                           SUM(estado = 'Pendiente') as pendientes
                    FROM Reportes WHERE idProfesional = :pid AND COALESCE(eliminado, 0) = 0
                """),
                {"pid": professional_id}
            ).mappings().one_or_none()
            evolucion_data = session.execute(
                text("""
                    SELECT
                        COUNT(DISTINCT c.idPaciente) as pacientes_con_citas,
                        COUNT(DISTINCT CASE WHEN e.fecha >= DATE_SUB(CURDATE(), INTERVAL 14 DAY) THEN e.idPaciente END) as pacientes_con_evolucion_reciente
                    FROM Citas c
                    LEFT JOIN EvolucionPaciente e ON e.idPaciente = c.idPaciente
                    WHERE c.idProfesional = :pid
                      AND c.estado != 'Cancelada'
                      AND c.fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                """),
                {"pid": professional_id}
            ).mappings().one_or_none()
            emocion_data = session.execute(
                text("""
                    SELECT
                        AVG(e.nivelEnergia) as nivel_energia_promedio,
                        COUNT(e.idEvolucion) as total_registros
                    FROM EvolucionPaciente e
                    JOIN Citas c ON c.idPaciente = e.idPaciente
                    WHERE c.idProfesional = :pid
                      AND c.estado != 'Cancelada'
                      AND e.fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                """),
                {"pid": professional_id}
            ).mappings().one_or_none()
            alertas_citas = session.execute(
                text("""
                    SELECT
                        COUNT(CASE WHEN c.estado = 'Pendiente' AND c.fecha = CURDATE() THEN 1 END) as citas_por_confirmar_hoy,
                        COUNT(CASE WHEN c.estado = 'Pendiente' AND c.fecha > CURDATE() AND c.fecha <= DATE_ADD(CURDATE(), INTERVAL 3 DAY) THEN 1 END) as citas_por_confirmar_proximas
                    FROM Citas c WHERE c.idProfesional = :pid
                """),
                {"pid": professional_id}
            ).mappings().one_or_none()
            alertas_reportes = session.execute(
                text("""
                    SELECT COUNT(*) as reportes_pendientes
                    FROM Reportes WHERE idProfesional = :pid AND estado = 'Pendiente' AND COALESCE(eliminado, 0) = 0
                """),
                {"pid": professional_id}
            ).mappings().one_or_none()

            pacientes_sin_evolucion = 0
            if evolucion_data:
                pc = evolucion_data.get("pacientes_con_citas") or 0
                per = evolucion_data.get("pacientes_con_evolucion_reciente") or 0
                pacientes_sin_evolucion = pc - per

            alertas = []
            if alertas_citas:
                if alertas_citas.get("citas_por_confirmar_hoy"):
                    alertas.append({"tipo": "warning", "icono": "fa-clock", "titulo": "Citas por confirmar hoy", "mensaje": f"{alertas_citas['citas_por_confirmar_hoy']} cita(s) pendiente(s) de confirmación", "accion": "ver_agenda"})
                if alertas_citas.get("citas_por_confirmar_proximas"):
                    alertas.append({"tipo": "info", "icono": "fa-calendar-day", "titulo": "Citas por confirmar (próx. 3 días)", "mensaje": f"{alertas_citas['citas_por_confirmar_proximas']} cita(s) pendiente(s)", "accion": "ver_agenda"})
            if alertas_reportes and alertas_reportes.get("reportes_pendientes"):
                alertas.append({"tipo": "warning", "icono": "fa-file-text", "titulo": "Reportes pendientes", "mensaje": f"{alertas_reportes['reportes_pendientes']} reporte(s) por completar", "accion": "ver_reportes"})
            if pacientes_sin_evolucion > 0:
                alertas.append({"tipo": "info", "icono": "fa-heart-pulse", "titulo": "Pacientes sin evolución reciente", "mensaje": f"{pacientes_sin_evolucion} paciente(s) sin registro en 14 días", "accion": "ver_pacientes"})

            return {
                "pacientes_activos": stats["pacientes_activos"] or 0 if stats else 0,
                "citas_hoy": stats["citas_hoy"] or 0 if stats else 0,
                "citas_pendientes": stats["citas_pendientes"] or 0 if stats else 0,
                "actividades": actividades,
                "proximas_citas": proximas_citas,
                "reportes": reportes_data and {"total": reportes_data.get("total_reportes") or 0, "completados": reportes_data.get("completados") or 0, "pendientes": reportes_data.get("pendientes") or 0},
                "evolucion": evolucion_data and {"pacientes_con_citas": evolucion_data.get("pacientes_con_citas") or 0, "pacientes_con_evolucion_reciente": evolucion_data.get("pacientes_con_evolucion_reciente") or 0, "pacientes_sin_evolucion": pacientes_sin_evolucion, "nivel_energia_promedio": round(emocion_data["nivel_energia_promedio"], 1) if emocion_data and emocion_data.get("nivel_energia_promedio") else None, "total_registros": emocion_data.get("total_registros") or 0} if emocion_data else None,
                "alertas": alertas,
            }

    def list_professional_patients(self, professional_id):
        with db_session() as session:
            rows = session.execute(
                text("""
                    SELECT DISTINCT r.idUsuario, r.nombre, r.fotoPerfil, p.edad, p.genero,
                           COALESCE(p.numeroTelefonico, r.email) as contacto,
                           (SELECT diagnostico FROM PacientesProfesional
                            WHERE idPaciente = r.idUsuario AND idProfesional = :pid
                            ORDER BY fechaDiagnostico DESC LIMIT 1) as ultimoDiagnostico
                    FROM Register r
                    JOIN PerfilPaciente p ON r.idUsuario = p.idPaciente
                    WHERE r.rol = 'paciente'
                    ORDER BY r.nombre
                """),
                {"pid": professional_id}
            ).mappings().all()
            return [dict(r) for r in rows]

    def list_patients_for_chat(self):
        with db_session() as session:
            rows = session.execute(
                text("""
                    SELECT r.idUsuario, r.nombre, r.fotoPerfil, p.edad, p.genero,
                           COALESCE(p.numeroTelefonico, r.email) as contacto
                    FROM Register r
                    LEFT JOIN PerfilPaciente p ON r.idUsuario = p.idPaciente
                    WHERE r.rol = 'paciente'
                    ORDER BY r.nombre
                """)
            ).mappings().all()
            return [dict(r) for r in rows]

    def save_diagnosis(self, professional_id, data):
        with db_session() as session:
            existing = session.execute(
                select(PacientesProfesional).where(
                    PacientesProfesional.idProfesional == professional_id,
                    PacientesProfesional.idPaciente == data.get("idPaciente"),
                )
            ).scalar_one_or_none()
            if existing:
                existing.sintomas = data.get("sintomas")
                existing.diagnostico = data.get("diagnostico")
                existing.tratamiento = data.get("tratamiento")
                existing.fechaDiagnostico = data.get("fecha_diagnostico")
            else:
                session.add(PacientesProfesional(
                    idProfesional=professional_id,
                    idPaciente=data.get("idPaciente"),
                    sintomas=data.get("sintomas"),
                    diagnostico=data.get("diagnostico"),
                    tratamiento=data.get("tratamiento"),
                    fechaDiagnostico=data.get("fecha_diagnostico"),
                ))

    def get_diagnosis_history(self, professional_id):
        with db_session() as session:
            rows = session.execute(
                text("""
                    SELECT r.nombre as paciente, pp.fechaDiagnostico as fechaRaw,
                           pp.sintomas, pp.diagnostico, pp.tratamiento
                    FROM PacientesProfesional pp
                    JOIN Register r ON pp.idPaciente = r.idUsuario
                    WHERE pp.idProfesional = :pid AND pp.diagnostico IS NOT NULL AND pp.diagnostico != ''
                    ORDER BY pp.fechaDiagnostico DESC
                """),
                {"pid": professional_id}
            ).mappings().all()
            return [dict(r) for r in rows]

    def get_report_overview(self, professional_id):
        with db_session() as session:
            stats = session.execute(
                text("""
                    SELECT COUNT(*) as total, SUM(estado = 'Completado') as completados,
                           SUM(estado = 'Pendiente') as pendientes
                    FROM Reportes WHERE idProfesional = :pid AND COALESCE(eliminado, 0) = 0
                """),
                {"pid": professional_id}
            ).mappings().one_or_none()
            reportes_rows = session.execute(
                text("""
                    SELECT rep.idReporte, rep.idPaciente, rep.tipoReporte, rep.estado,
                           DATE_FORMAT(rep.fechaInicio, '%d/%m/%Y') as fechaInicio,
                           DATE_FORMAT(rep.fechaFin, '%d/%m/%Y') as fechaFin,
                           rep.sintomas, rep.diagnostico, rep.tratamiento,
                           COALESCE(r.nombre, 'General') as paciente
                    FROM Reportes rep
                    LEFT JOIN Register r ON rep.idPaciente = r.idUsuario
                    WHERE rep.idProfesional = :pid AND COALESCE(eliminado, 0) = 0
                    ORDER BY rep.fechaInicio DESC
                """),
                {"pid": professional_id}
            ).mappings().all()
            reportes = [dict(r) for r in reportes_rows]
            pacientes_rows = session.execute(
                text("""
                    SELECT DISTINCT r.idUsuario, r.nombre
                    FROM Register r
                    JOIN Citas c ON c.idPaciente = r.idUsuario
                    WHERE c.idProfesional = :pid
                      AND r.rol = 'paciente'
                      AND LOWER(COALESCE(c.estado, '')) != 'cancelada'
                    ORDER BY r.nombre
                """),
                {"pid": professional_id}
            ).mappings().all()
            pacientes = [dict(r) for r in pacientes_rows]
            return {"stats": dict(stats) if stats else {}, "reportes": reportes, "pacientes": pacientes}

    def create_report(self, professional_id, data):
        with db_session() as session:
            session.add(Reportes(
                idProfesional=professional_id,
                idPaciente=data.get("idPaciente") or None,
                tipoReporte=data.get("tipoReporte"),
                fechaInicio=data.get("fechaInicio") or None,
                fechaFin=data.get("fechaFin") or None,
                sintomas=data.get("sintomas"),
                diagnostico=data.get("diagnostico"),
                tratamiento=data.get("tratamiento"),
                estado="Completado",
            ))

    def get_latest_patient_diagnosis(self, professional_id, patient_id):
        with db_session() as session:
            stmt = select(PacientesProfesional).where(
                PacientesProfesional.idProfesional == professional_id,
                PacientesProfesional.idPaciente == patient_id,
            ).order_by(PacientesProfesional.fechaDiagnostico.desc()).limit(1)
            pp = session.execute(stmt).scalar_one_or_none()
            if pp:
                return {"sintomas": pp.sintomas, "diagnostico": pp.diagnostico, "tratamiento": pp.tratamiento}
            return None

    def update_report(self, professional_id, data):
        with db_session() as session:
            stmt = select(Reportes).where(
                Reportes.idReporte == data.get("idReporte"),
                Reportes.idProfesional == professional_id,
            )
            report = session.execute(stmt).scalar_one_or_none()
            if report:
                report.tipoReporte = data.get("tipoReporte")
                report.estado = data.get("estado")

    def delete_report(self, professional_id, report_id):
        with db_session() as session:
            stmt = select(Reportes).where(
                Reportes.idReporte == report_id,
                Reportes.idProfesional == professional_id,
            )
            report = session.execute(stmt).scalar_one_or_none()
            if report:
                report.eliminado = True

    def get_deleted_reports(self, professional_id):
        with db_session() as session:
            rows = session.execute(
                text("""
                    SELECT rep.idReporte, rep.idPaciente, rep.tipoReporte, rep.estado,
                           DATE_FORMAT(rep.fechaInicio, '%d/%m/%Y') as fechaInicio,
                           DATE_FORMAT(rep.fechaFin, '%d/%m/%Y') as fechaFin,
                           COALESCE(r.nombre, 'General') as paciente
                    FROM Reportes rep
                    LEFT JOIN Register r ON rep.idPaciente = r.idUsuario
                    WHERE rep.idProfesional = :pid AND rep.eliminado = 1
                    ORDER BY rep.fechaInicio DESC
                """),
                {"pid": professional_id}
            ).mappings().all()
            return [dict(r) for r in rows]

    def get_all_patient_evolution(self, professional_id):
        with db_session() as session:
            rows = session.execute(
                text("""
                    SELECT e.idEvolucion, e.idPaciente, e.estadoEmocional, e.nivelEnergia,
                           e.notasPersonales, DATE_FORMAT(e.fecha, '%d/%m/%Y') as fecha,
                           e.fecha as fechaRaw, r.nombre as paciente
                    FROM EvolucionPaciente e
                    JOIN Register r ON e.idPaciente = r.idUsuario
                    WHERE r.rol = 'paciente'
                    ORDER BY e.fecha DESC
                """)
            ).mappings().all()
            return [dict(r) for r in rows]

    def professional_has_patient(self, professional_id, patient_id):
        with db_session() as session:
            count = session.execute(
                select(func.count()).select_from(Citas).where(
                    Citas.idProfesional == professional_id,
                    Citas.idPaciente == patient_id,
                    func.lower(func.coalesce(Citas.estado, "")) != "cancelada",
                ).limit(1)
            ).scalar() or 0
            return count > 0
