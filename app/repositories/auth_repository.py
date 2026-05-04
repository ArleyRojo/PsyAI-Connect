import logging
from datetime import datetime
from app.utils.db import db_cursor

logger = logging.getLogger(__name__)


def get_user_by_email(email, *, admin_only=False):
    with db_cursor(dictionary=True) as (_, cursor):
        if admin_only:
            cursor.execute(
                """
                SELECT idUsuario, nombre, email, contrasena, rol, estadoCuenta, fechaRegistro, fotoPerfil
                FROM Register
                WHERE email = %s AND rol = 'admin' AND estadoCuenta = 'Activa'
                """,
                (email,),
            )
        else:
            cursor.execute(
                """
                SELECT idUsuario, nombre, email, contrasena, rol, estadoCuenta, fechaRegistro, fotoPerfil
                FROM Register
                WHERE email = %s AND estadoCuenta = 'Activa'
                """,
                (email,),
            )
        return cursor.fetchone()


def user_exists_by_email(email):
    with db_cursor() as (_, cursor):
        cursor.execute("SELECT idUsuario FROM Register WHERE email = %s", (email,))
        return cursor.fetchone() is not None


def create_user(nombre, email, password_hash, rol, genero):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "INSERT INTO Register (nombre, email, contrasena, rol) VALUES (%s, %s, %s, %s)",
            (nombre, email, password_hash, rol),
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
        if rol == "paciente":
            cursor.execute(
                "INSERT INTO PerfilPaciente (idPaciente, genero) VALUES (%s, %s)",
                (nuevo_id, genero),
            )
        else:
            cursor.execute("INSERT INTO PerfilProfesional (idProfesional) VALUES (%s)", (nuevo_id,))
        conn.commit()
        return nuevo_id


def register_login_event(user_id, email, ip_address="unknown"):
    with db_cursor() as (conn, cursor):
        try:
            cursor.execute(
                "INSERT INTO Login (idUsuario, email) VALUES (%s, %s)",
                (user_id, email),
            )
        except Exception as e:
            logger.error(f"Error registering login event: {e}")
        cursor.execute(
            "INSERT INTO AuditoriaAccesos (idUsuario, accion, ip) VALUES (%s, %s, %s)",
            (user_id, "Login exitoso", ip_address),
        )
        conn.commit()


def active_user_exists_by_email(email):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT idUsuario FROM Register WHERE email = %s AND estadoCuenta = 'Activa'",
            (email,),
        )
        return cursor.fetchone() is not None


def create_password_recovery_token(email, token, expires):
    with db_cursor(dictionary=True) as (conn, cursor):
        cursor.execute(
            "SELECT idUsuario FROM Register WHERE email = %s",
            (email,),
        )
        user = cursor.fetchone()
        if user:
            cursor.execute(
                "INSERT INTO RecoveryTokens (idUsuario, token, expires) VALUES (%s, %s, %s)",
                (user["idUsuario"], token, expires),
            )
            conn.commit()


def validate_recovery_token(token):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT idUsuario, expires FROM RecoveryTokens WHERE token = %s AND used = 0",
            (token,),
        )
        result = cursor.fetchone()
        if not result:
            return None
        if result["expires"] < datetime.now():
            return None
        return result["idUsuario"]


def invalidate_recovery_token(token):
    with db_cursor(dictionary=True) as (conn, cursor):
        cursor.execute(
            "UPDATE RecoveryTokens SET used = 1 WHERE token = %s",
            (token,),
        )
        conn.commit()
        return cursor.rowcount > 0


def update_password(user_id, new_password_hash):
    with db_cursor(dictionary=True) as (conn, cursor):
        cursor.execute(
            "UPDATE Register SET contrasena = %s WHERE idUsuario = %s",
            (new_password_hash, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0