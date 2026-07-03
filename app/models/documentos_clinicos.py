from datetime import datetime
from sqlalchemy import Integer, String, Text, Enum, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class DocumentosClinicos(Base):
    __tablename__ = "DocumentosClinicos"

    idDocumento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idProfesional: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    idPaciente: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    nombreArchivo: Mapped[str] = mapped_column(String(255), nullable=False)
    rutaArchivo: Mapped[str] = mapped_column(String(500), nullable=False)
    tipoMime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tamanoArchivo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    categoria: Mapped[str | None] = mapped_column(Enum("Historia Clinica", "Evolucion", "Diagnostico", "Consentimiento", "Otro"), default="Otro")
    visibilidad: Mapped[str | None] = mapped_column(Enum("privado", "compartido"), default="privado")
    notasInternas: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    eliminado: Mapped[bool | None] = mapped_column(Boolean, default=False)

    profesional = relationship("Register", back_populates="documentos_clinicos", foreign_keys=[idProfesional])
    paciente = relationship("Register", back_populates="documentos_paciente_prof", foreign_keys=[idPaciente])

    def to_dict(self):
        return {
            "idDocumento": self.idDocumento,
            "idProfesional": self.idProfesional,
            "idPaciente": self.idPaciente,
            "nombreArchivo": self.nombreArchivo,
            "rutaArchivo": self.rutaArchivo,
            "tipoMime": self.tipoMime,
            "tamanoArchivo": self.tamanoArchivo,
            "categoria": self.categoria,
            "visibilidad": self.visibilidad,
            "notasInternas": self.notasInternas,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "eliminado": self.eliminado,
        }
