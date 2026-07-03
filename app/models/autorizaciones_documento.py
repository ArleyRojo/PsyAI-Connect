from datetime import datetime
from sqlalchemy import Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AutorizacionesDocumento(Base):
    __tablename__ = "AutorizacionesDocumento"

    idAutorizacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idDocumento: Mapped[int] = mapped_column(Integer, ForeignKey("DocumentosClinicos.idDocumento", ondelete="CASCADE"), nullable=False)
    idProfesional: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    fechaAutorizacion: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    revocado: Mapped[bool | None] = mapped_column(Boolean, default=False)
    fechaRevocacion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "idAutorizacion": self.idAutorizacion,
            "idDocumento": self.idDocumento,
            "idProfesional": self.idProfesional,
            "fechaAutorizacion": self.fechaAutorizacion.isoformat() if self.fechaAutorizacion else None,
            "revocado": self.revocado,
            "fechaRevocacion": self.fechaRevocacion.isoformat() if self.fechaRevocacion else None,
        }
