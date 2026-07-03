from datetime import datetime
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError
from app.database.session import db_session
from app.models.intentos_fallidos import IntentosFallidos


class SecurityRepository:
    def check_brute_force(self, email):
        try:
            with db_session() as session:
                stmt = select(IntentosFallidos).where(IntentosFallidos.email == email)
                row = session.execute(stmt).scalar_one_or_none()
                if not row:
                    return False, 0
                if row.intentos < 5:
                    return False, 0
                if not row.bloqueado_hasta:
                    return False, 0
                ahora = datetime.now()
                if row.bloqueado_hasta <= ahora:
                    return False, 0
                segundos = int((row.bloqueado_hasta - ahora).total_seconds())
                return True, segundos
        except Exception:
            return False, 0

    def register_failed_attempt(self, email):
        ahora = datetime.now()
        try:
            with db_session() as session:
                stmt = select(IntentosFallidos).where(IntentosFallidos.email == email)
                row = session.execute(stmt).scalar_one_or_none()
                if row:
                    row.intentos += 1
                    row.ultimo_intento = ahora
                    if row.intentos >= 5:
                        from datetime import timedelta
                        row.bloqueado_hasta = ahora + timedelta(minutes=15)
                else:
                    session.add(IntentosFallidos(
                        email=email, intentos=1, ultimo_intento=ahora,
                    ))
        except Exception:
            return

    def reset_failed_attempts(self, email):
        try:
            with db_session() as session:
                stmt = select(IntentosFallidos).where(IntentosFallidos.email == email)
                row = session.execute(stmt).scalar_one_or_none()
                if row:
                    row.intentos = 0
                    row.bloqueado_hasta = None
        except Exception:
            return
