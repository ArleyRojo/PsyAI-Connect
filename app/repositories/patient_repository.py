from sqlalchemy import select
from app.database.session import db_session
from app.models.register import Register
from app.models.perfil_paciente import PerfilPaciente
from app.models.perfil_profesional import PerfilProfesional
from app.models.encuesta_chatbot import EncuestaChatbot
from app.models.evolucion_paciente import EvolucionPaciente


class PatientRepository:
    def update_profile_photo(self, filename, user_id):
        with db_session() as session:
            user = session.get(Register, user_id)
            if user:
                user.fotoPerfil = filename

    def save_chatbot_survey(self, user_id, data):
        with db_session() as session:
            session.add(EncuestaChatbot(
                idPaciente=user_id,
                utilidad=data.get("utilidad"),
                claridad=data.get("claridad"),
                recomendaria=data.get("recomendaria"),
                comentario=data.get("comentario"),
            ))

    def get_patient_profile(self, user_id):
        with db_session() as session:
            user = session.get(Register, user_id)
            if not user:
                return None
            perfil = session.get(PerfilPaciente, user_id)
            return {
                "nombre": user.nombre,
                "email": user.email,
                "fotoPerfil": user.fotoPerfil,
                "fechaRegistro": user.fechaRegistro,
                "edad": perfil.edad if perfil else None,
                "genero": perfil.genero if perfil else None,
                "numeroTelefonico": perfil.numeroTelefonico if perfil else None,
                "consentimiento_chatbot": perfil.consentimiento_chatbot if perfil else None,
            }

    def update_patient_profile(self, data):
        with db_session() as session:
            perfil = session.get(PerfilPaciente, data.get("idUsuario"))
            if perfil:
                perfil.numeroTelefonico = data.get("numeroTelefonico")
            else:
                session.add(PerfilPaciente(
                    idPaciente=data.get("idUsuario"),
                    numeroTelefonico=data.get("numeroTelefonico"),
                    consentimiento_chatbot=False,
                ))

    def get_chatbot_consent(self, user_id):
        with db_session() as session:
            perfil = session.get(PerfilPaciente, user_id)
            return bool(perfil.consentimiento_chatbot) if perfil else False

    def update_chatbot_consent(self, user_id, consent):
        with db_session() as session:
            perfil = session.get(PerfilPaciente, user_id)
            if perfil:
                perfil.consentimiento_chatbot = bool(consent)
            else:
                session.add(PerfilPaciente(
                    idPaciente=user_id,
                    consentimiento_chatbot=bool(consent),
                ))

    def create_patient_evolution(self, user_id, data):
        with db_session() as session:
            session.add(EvolucionPaciente(
                idPaciente=user_id,
                estadoEmocional=data.get("estadoEmocional"),
                nivelEnergia=data.get("nivelEnergia"),
                notasPersonales=data.get("notasPersonales"),
            ))

    def get_patient_evolution_history(self, user_id):
        with db_session() as session:
            stmt = select(EvolucionPaciente).where(
                EvolucionPaciente.idPaciente == user_id
            ).order_by(EvolucionPaciente.fecha.desc())
            rows = session.execute(stmt).scalars().all()
            result = []
            for r in rows:
                result.append({
                    "estadoEmocional": r.estadoEmocional,
                    "nivelEnergia": r.nivelEnergia,
                    "notasPersonales": r.notasPersonales,
                    "fecha": r.fecha.strftime("%d/%m/%Y") if r.fecha else None,
                    "fechaRaw": r.fecha,
                })
            return result

    def list_patients(self, page=1, limit=20):
        offset = (page - 1) * limit
        with db_session() as session:
            stmt = select(Register).where(
                Register.rol == "paciente"
            ).order_by(Register.nombre).limit(limit).offset(offset)
            users = session.execute(stmt).scalars().all()
            return [
                {"idUsuario": u.idUsuario, "nombre": u.nombre, "email": u.email, "fotoPerfil": u.fotoPerfil}
                for u in users
            ]

    def list_professionals(self):
        with db_session() as session:
            stmt = select(Register.idUsuario, Register.nombre).where(
                Register.rol == "profesional"
            ).order_by(Register.nombre)
            rows = session.execute(stmt).all()
            return [{"idUsuario": r[0], "nombre": r[1]} for r in rows]

    def list_professionals_for_patient(self, patient_id):
        with db_session() as session:
            stmt = select(
                Register.idUsuario, Register.nombre, Register.fotoPerfil,
                PerfilProfesional.especialidad,
            ).outerjoin(
                PerfilProfesional, Register.idUsuario == PerfilProfesional.idProfesional
            ).where(Register.rol == "profesional").order_by(Register.nombre)
            rows = session.execute(stmt).all()
            return [
                {"idUsuario": r[0], "nombre": r[1], "fotoPerfil": r[2], "especialidad": r[3]}
                for r in rows
            ]
