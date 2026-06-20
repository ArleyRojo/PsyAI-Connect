from datetime import datetime

from flask import current_app
from mysql.connector.errors import ProgrammingError

from app.utils.db import db_cursor


def _table_not_found(e):
    return e.errno == 1146


def check_brute_force(email):
    """Retorna (bloqueado, segundos_restantes) para el email dado."""
    try:
        with db_cursor(dictionary=True) as (_, cursor):
            cursor.execute(
                "SELECT intentos, bloqueado_hasta FROM intentos_fallidos WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
    except ProgrammingError as e:
        if _table_not_found(e):
            current_app.logger.error("Tabla intentos_fallidos no existe en check_brute_force: %s", e)
            return False, 0
        raise
    if not row:
        return False, 0
    if row["intentos"] < 5:
        return False, 0
    bloqueado_hasta = row["bloqueado_hasta"]
    if not bloqueado_hasta:
        return False, 0
    ahora = datetime.now()
    if bloqueado_hasta <= ahora:
        return False, 0
    segundos = int((bloqueado_hasta - ahora).total_seconds())
    return True, segundos


def register_failed_attempt(email):
    """Incrementa contador de intentos. Si llega a 5, bloquea 15 min."""
    ahora = datetime.now()
    try:
        with db_cursor(dictionary=True) as (conn, cursor):
            cursor.execute(
                "SELECT id FROM intentos_fallidos WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    """
                    UPDATE intentos_fallidos
                    SET intentos = intentos + 1,
                        ultimo_intento = %s,
                        bloqueado_hasta = IF(intentos >= 4, DATE_ADD(%s, INTERVAL 15 MINUTE), NULL)
                    WHERE email = %s
                    """,
                    (ahora, ahora, email),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO intentos_fallidos (email, intentos, ultimo_intento, bloqueado_hasta)
                    VALUES (%s, 1, %s, NULL)
                    """,
                    (email, ahora),
                )
            conn.commit()
    except ProgrammingError as e:
        if _table_not_found(e):
            current_app.logger.error("Tabla intentos_fallidos no existe en register_failed_attempt: %s", e)
            return
        raise


def reset_failed_attempts(email):
    """Reinicia contador tras login exitoso."""
    try:
        with db_cursor(dictionary=True) as (conn, cursor):
            cursor.execute(
                "UPDATE intentos_fallidos SET intentos = 0, bloqueado_hasta = NULL WHERE email = %s",
                (email,),
            )
            conn.commit()
    except ProgrammingError as e:
        if _table_not_found(e):
            current_app.logger.error("Tabla intentos_fallidos no existe en reset_failed_attempts: %s", e)
            return
        raise
