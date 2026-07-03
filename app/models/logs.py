from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Logs(Base):
    __tablename__ = "Logs"

    idLog: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    administrador: Mapped[str | None] = mapped_column(String(120), nullable=True)
    modulo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    accion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    rol_anterior: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rol_nuevo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    usuario_afectado: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def to_dict(self):
        return {
            "idLog": self.idLog,
            "administrador": self.administrador,
            "modulo": self.modulo,
            "accion": self.accion,
            "detalle": self.detalle,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "rol_anterior": self.rol_anterior,
            "rol_nuevo": self.rol_nuevo,
            "usuario_afectado": self.usuario_afectado,
        }
