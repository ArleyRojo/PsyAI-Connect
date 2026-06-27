# ============================================================
# ARCHIVO: repositories/mensajes_repository.py
# ============================================================

from app.utils.db import db_cursor


def enviar_mensaje(id_emisor, id_receptor, mensaje):
    # Inserta un nuevo mensaje en la conversación entre dos usuarios
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO MensajesChat (idEmisor, idReceptor, mensaje)
            VALUES (%s, %s, %s)
            """,
            (id_emisor, id_receptor, mensaje),
        )
        conn.commit()
        return cursor.lastrowid


def get_conversacion(id_usuario, id_otro, desde_id=0, limit=60):
    """Devuelve mensajes entre dos usuarios. Si desde_id > 0, solo los nuevos."""
    with db_cursor(dictionary=True) as (_, cursor):
        if desde_id <= 0:
            # Carga inicial: obtiene los últimos N mensajes ordenados cronológicamente
            cursor.execute(
                """
                SELECT *
                FROM (
                    SELECT
                        idMensaje,
                        idEmisor,
                        idReceptor,
                        mensaje,
                        leido,
                        fecha
                    FROM MensajesChat
                    WHERE
                        (idEmisor = %s AND idReceptor = %s) OR
                        (idEmisor = %s AND idReceptor = %s)
                    ORDER BY fecha DESC, idMensaje DESC
                    LIMIT %s
                ) recientes
                ORDER BY fecha ASC, idMensaje ASC
                """,
                (id_usuario, id_otro, id_otro, id_usuario, limit),
            )
            return cursor.fetchall()

        # Mensajes nuevos desde un ID específico (para polling incremental)
        cursor.execute(
            """
            SELECT
                idMensaje,
                idEmisor,
                idReceptor,
                mensaje,
                leido,
                fecha
            FROM MensajesChat
            WHERE
                idMensaje > %s AND (
                    (idEmisor = %s AND idReceptor = %s) OR
                    (idEmisor = %s AND idReceptor = %s)
                )
            ORDER BY fecha ASC, idMensaje ASC
            LIMIT %s
            """,
            (desde_id, id_usuario, id_otro, id_otro, id_usuario, limit),
        )
        return cursor.fetchall()


def marcar_leidos(id_receptor, id_emisor):
    # Marca como leídos todos los mensajes no leídos de un emisor específico
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            UPDATE MensajesChat
            SET leido = 1
            WHERE idReceptor = %s AND idEmisor = %s AND leido = 0
            """,
            (id_receptor, id_emisor),
        )
        conn.commit()


def contar_no_leidos(id_receptor, id_emisor):
    # Cuenta los mensajes no leídos de una conversación específica
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT COUNT(*) as total FROM MensajesChat
            WHERE idReceptor = %s AND idEmisor = %s AND leido = 0
            """,
            (id_receptor, id_emisor),
        )
        row = cursor.fetchone()
        return row["total"] if row else 0


def get_ultimo_mensaje(id_usuario, id_otro):
    # Obtiene el mensaje más reciente entre dos usuarios
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT idMensaje, idEmisor, mensaje, fecha
            FROM MensajesChat
            WHERE
                (idEmisor = %s AND idReceptor = %s) OR
                (idEmisor = %s AND idReceptor = %s)
            ORDER BY fecha DESC
            LIMIT 1
            """,
            (id_usuario, id_otro, id_otro, id_usuario),
        )
        return cursor.fetchone()
