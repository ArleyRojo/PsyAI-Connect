from datetime import datetime, date
from sqlalchemy import Integer, String, Text, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class PacientesProfesional(Base):
    __tablename__ = "PacientesProfesional"
    __table_args__ = (
        UniqueConstraint("idProfesional", "idPaciente", name="uq_profesional_paciente"),
    )

    idRegistro: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idProfesional: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    idPaciente: Mapped[int | None] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=True)
    sintomas: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnostico: Mapped[str | None] = mapped_column(Text, nullable=True)
    tratamiento: Mapped[str | None] = mapped_column(Text, nullable=True)
    fechaDiagnostico: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    profesional = relationship("Register", back_populates="pacientes_profesional", foreign_keys=[idProfesional])
    paciente = relationship("Register", back_populates="pacientes_asignados", foreign_keys=[idPaciente])

    def to_dict(self):
        return {
            "idRegistro": self.idRegistro,
            "idProfesional": self.idProfesional,
            "idPaciente": self.idPaciente,
            "sintomas": self.sintomas,
            "diagnostico": self.diagnostico,
            "tratamiento": self.tratamiento,
            "fechaDiagnostico": self.fechaDiagnostico.isoformat() if self.fechaDiagnostico else None,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }
