# ARCHIVO: utils/db.py
# Context manager db_cursor que obtiene una conexión del pool, provee cursor,
# hace rollback en error y cierra cursor + conexión al salir (así o en finally).
from contextlib import contextmanager

from app.database.connection import get_connection


@contextmanager
def db_cursor(*, dictionary=False):
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=dictionary)
        yield conn, cursor
    except Exception:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass