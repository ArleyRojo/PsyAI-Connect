from contextlib import contextmanager

from app.database.connection import get_connection


@contextmanager
def db_cursor(*, dictionary=False, buffered=True):
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=dictionary, buffered=buffered)
        yield conn, cursor
        if cursor and not cursor.with_rows:
            conn.commit()
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
                if getattr(cursor, 'with_rows', False):
                    cursor.fetchall()
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                try:
                    if conn.unread_results:
                        conn.get_rows()
                except Exception:
                    pass
                conn.close()
        except Exception:
            pass