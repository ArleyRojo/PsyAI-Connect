from contextlib import contextmanager

from app.database.connection import get_connection


class DbSessionManager:
    def __init__(self, get_conn):
        self._get_conn = get_conn

    @contextmanager
    def db_cursor(self, *, dictionary=False):
        conn = cursor = None
        try:
            conn = self._get_conn()
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


_manager = DbSessionManager(get_connection)
db_cursor = _manager.db_cursor
