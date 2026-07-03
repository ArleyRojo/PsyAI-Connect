from datetime import datetime, date
from sqlalchemy import Integer, String, Text, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Reportes(Base):
    __tablename__ = "Reportes"

    idReporte: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idProfesional: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    idPaciente: Mapped[int | None] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=True)
    tipoReporte: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fechaInicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    fechaFin: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str | None] = mapped_column(String(20), default="Pendiente")
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    eliminado: Mapped[bool | None] = mapped_column(Boolean, default=False)
    sintomas: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnostico: Mapped[str | None] = mapped_column(Text, nullable=True)
    tratamiento: Mapped[str | None] = mapped_column(Text, nullable=True)

    profesional = relationship("Register", back_populates="reportes_profesional", foreign_keys=[idProfesional])
    paciente = relationship("Register", back_populates="reportes_paciente", foreign_keys=[idPaciente])

    def to_dict(self):
        return {
            "idReporte": self.idReporte,
            "idProfesional": self.idProfesional,
            "idPaciente": self.idPaciente,
            "tipoReporte": self.tipoReporte,
            "fechaInicio": self.fechaInicio.isoformat() if self.fechaInicio else None,
            "fechaFin": self.fechaFin.isoformat() if self.fechaFin else None,
            "estado": self.estado,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "eliminado": self.eliminado,
            "sintomas": self.sintomas,
            "diagnostico": self.diagnostico,
            "tratamiento": self.tratamiento,
        }
