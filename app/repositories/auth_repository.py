import logging
from datetime import datetime
from sqlalchemy import select
from app.database.session import db_session
from app.models.register import Register
from app.models.perfil_paciente import PerfilPaciente
from app.models.perfil_profesional import PerfilProfesional
from app.models.login import Login
from app.models.auditoria_accesos import AuditoriaAccesos
from app.models.recovery_tokens import RecoveryTokens

logger = logging.getLogger(__name__)


class AuthRepository:
    def get_user_by_email(self, email, *, admin_only=False):
        with db_session() as session:
            stmt = select(Register).where(
                Register.email == email,
                Register.estadoCuenta == "Activa",
            )
            if admin_only:
                stmt = stmt.where(Register.rol == "admin")
            user = session.execute(stmt).scalar_one_or_none()
            if user:
                return user.to_dict()
            return None

    def user_exists_by_email(self, email):
        with db_session() as session:
            stmt = select(Register.idUsuario).where(Register.email == email)
            return session.execute(stmt).scalar_one_or_none() is not None

    def create_user(self, nombre, email, password_hash, rol, genero, edad=None):
        with db_session() as session:
            user = Register(
                nombre=nombre, email=email,
                contrasena=password_hash, rol=rol,
            )
            session.add(user)
            session.flush()
            if rol == "paciente":
                session.add(PerfilPaciente(idPaciente=user.idUsuario, genero=genero, edad=edad))
            else:
                session.add(PerfilProfesional(idProfesional=user.idUsuario, genero=genero, edad=edad))
            return user.idUsuario

    def register_login_event(self, user_id, email, ip_address="unknown"):
        with db_session() as session:
            try:
                session.add(Login(idUsuario=user_id, email=email))
            except Exception as e:
                logger.error(f"Error registering login event: {e}")
            session.add(AuditoriaAccesos(idUsuario=user_id, accion="Login exitoso", ip=ip_address))
            from app.repositories.admin_repository import AdminRepository
            AdminRepository.increment_logs_version()

    def active_user_exists_by_email(self, email):
        with db_session() as session:
            stmt = select(Register.idUsuario).where(
                Register.email == email,
                Register.estadoCuenta == "Activa",
            )
            return session.execute(stmt).scalar_one_or_none() is not None

    def create_password_recovery_token(self, email, token, expires):
        with db_session() as session:
            stmt = select(Register).where(Register.email == email)
            user = session.execute(stmt).scalar_one_or_none()
            if user:
                old_tokens = session.execute(
                    select(RecoveryTokens).where(
                        RecoveryTokens.idUsuario == user.idUsuario,
                        RecoveryTokens.used == False,
                    )
                ).scalars().all()
                for t in old_tokens:
                    t.used = True
                session.add(RecoveryTokens(idUsuario=user.idUsuario, token=token, expires=expires))

    def validate_recovery_token(self, token):
        with db_session() as session:
            stmt = select(RecoveryTokens).where(
                RecoveryTokens.token == token,
                RecoveryTokens.used == False,
            )
            rt = session.execute(stmt).scalar_one_or_none()
            if not rt:
                return None
            if rt.expires < datetime.now():
                return None
            return rt.idUsuario

    def invalidate_recovery_token(self, token):
        with db_session() as session:
            stmt = select(RecoveryTokens).where(RecoveryTokens.token == token)
            rt = session.execute(stmt).scalar_one_or_none()
            if rt:
                rt.used = True
                return True
            return False

    def update_password(self, user_id, new_password_hash):
        with db_session() as session:
            user = session.get(Register, user_id)
            if user:
                user.contrasena = new_password_hash
                return True
            return False
