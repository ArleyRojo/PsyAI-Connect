import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


class DatabaseSession:
    def __init__(self):
        self.engine = create_engine(
            f"mysql+mysqlconnector://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', 'root')}@"
            f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/"
            f"{os.getenv('DB_NAME', 'psyai_connect')}?charset=utf8mb4",
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        SessionFactory = sessionmaker(bind=self.engine)
        self.ScopedSession = scoped_session(SessionFactory)

    @contextmanager
    def db_session(self):
        session = self.ScopedSession()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


_db = DatabaseSession()
engine = _db.engine
db_session = _db.db_session
