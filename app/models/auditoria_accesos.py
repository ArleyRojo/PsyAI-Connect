from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class AuditoriaAccesos(Base):
    __tablename__ = "AuditoriaAccesos"

    idAuditoria: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idUsuario: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    accion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    usuario = relationship("Register", back_populates="accesos")

    def to_dict(self):
        return {
            "idAuditoria": self.idAuditoria,
            "idUsuario": self.idUsuario,
            "accion": self.accion,
            "ip": self.ip,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }
