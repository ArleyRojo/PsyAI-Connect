from sqlalchemy import select, func
from app.database.session import db_session
from app.models.conversaciones_chatbot import ConversacionesChatbot
from app.models.register import Register
from app.models.pacientes_profesional import PacientesProfesional
from app.models.notificaciones import Notificaciones
from app.models.citas import Citas


class ChatRepository:
    def save_conversation(self, patient_id, mensaje_usuario, respuesta_bot, nivel_emocional, palabras_riesgo):
        with db_session() as session:
            session.add(ConversacionesChatbot(
                idPaciente=patient_id,
                mensajeUsuario=mensaje_usuario,
                respuestaChatbot=respuesta_bot,
                nivelEmocionalDetectado=nivel_emocional,
                palabrasRiesgoDetectadas=palabras_riesgo,
            ))

    def get_history(self, patient_id, limit=40, today_only=False):
        with db_session() as session:
            stmt = select(
                ConversacionesChatbot.mensajeUsuario,
                ConversacionesChatbot.respuestaChatbot,
            ).where(ConversacionesChatbot.idPaciente == patient_id)
            if today_only:
                stmt = stmt.where(func.date(ConversacionesChatbot.fecha) == func.curdate())
            stmt = stmt.order_by(ConversacionesChatbot.fecha.desc()).limit(limit)
            rows = list(reversed(session.execute(stmt).all()))
            historial = []
            for row in rows:
                if row[0]:
                    historial.append({"tipo": "usuario", "mensaje": row[0]})
                if row[1]:
                    historial.append({"tipo": "bot", "mensaje": row[1]})
            return historial

    def delete_history(self, patient_id):
        with db_session() as session:
            conversaciones = session.execute(
                select(ConversacionesChatbot).where(ConversacionesChatbot.idPaciente == patient_id)
            ).scalars().all()
            for c in conversaciones:
                session.delete(c)

    def count_today_messages(self, patient_id):
        with db_session() as session:
            return session.execute(
                select(func.count()).select_from(ConversacionesChatbot).where(
                    ConversacionesChatbot.idPaciente == patient_id,
                    func.date(ConversacionesChatbot.fecha) == func.curdate(),
                )
            ).scalar() or 0

    def get_assigned_professionals(self, patient_id):
        with db_session() as session:
            rows = session.execute(
                select(PacientesProfesional.idProfesional).where(
                    PacientesProfesional.idPaciente == patient_id,
                    PacientesProfesional.idProfesional.isnot(None),
                )
            ).all()
            return [r[0] for r in rows]

    def get_all_professional_ids(self):
        with db_session() as session:
            rows = session.execute(
                select(Register.idUsuario).where(Register.rol == "profesional")
            ).all()
            return [r[0] for r in rows]

    def get_patient_name(self, patient_id):
        with db_session() as session:
            user = session.get(Register, patient_id)
            return user.nombre if user else None

    def notificacion_reciente_existe(self, patient_name, tipo, horas=12):
        with db_session() as session:
            stmt = select(func.count()).select_from(Notificaciones).where(
                Notificaciones.tipo == tipo,
                Notificaciones.mensaje.like(f"%{patient_name}%"),
                Notificaciones.fecha >= func.now() - func.make_interval(0, 0, 0, 0, horas, 0, 0),
            ).limit(1)
            count = session.execute(stmt).scalar() or 0
            return count > 0

    def get_low_risk_counts_for_professional(self, professional_id, days=7):
        from sqlalchemy import text
        with db_session() as session:
            rows = session.execute(
                text("""
                    SELECT c.idPaciente, COUNT(*) as total
                    FROM conversacioneschatbot c
                    JOIN Register r ON r.idUsuario = c.idPaciente AND r.rol = 'paciente'
                    LEFT JOIN PacientesProfesional pp ON pp.idPaciente = c.idPaciente AND pp.idProfesional = :prof
                    LEFT JOIN Citas cit ON cit.idPaciente = c.idPaciente AND cit.idProfesional = :prof2
                    WHERE c.nivelEmocionalDetectado = 'Bajo'
                      AND c.fecha >= DATE_SUB(NOW(), INTERVAL :days DAY)
                      AND (
                        pp.idRegistro IS NOT NULL
                        OR (cit.idCita IS NOT NULL AND LOWER(COALESCE(cit.estado, '')) != 'cancelada')
                      )
                    GROUP BY c.idPaciente
                """),
                {"prof": professional_id, "prof2": professional_id, "days": days}
            ).all()
            return {str(r[0]): r[1] for r in rows}
