from datetime import datetime
from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class DocumentosPaciente(Base):
    __tablename__ = "DocumentosPaciente"

    idDocumento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idPaciente: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    nombreArchivo: Mapped[str] = mapped_column(String(255), nullable=False)
    rutaArchivo: Mapped[str] = mapped_column(String(500), nullable=False)
    tipoMime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tamanoArchivo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    eliminado: Mapped[bool | None] = mapped_column(Boolean, default=False)

    paciente = relationship("Register", back_populates="documentos_paciente")

    def to_dict(self):
        return {
            "idDocumento": self.idDocumento,
            "idPaciente": self.idPaciente,
            "nombreArchivo": self.nombreArchivo,
            "rutaArchivo": self.rutaArchivo,
            "tipoMime": self.tipoMime,
            "tamanoArchivo": self.tamanoArchivo,
            "descripcion": self.descripcion,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "eliminado": self.eliminado,
        }
