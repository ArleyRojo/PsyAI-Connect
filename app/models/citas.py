from datetime import date, time, datetime
from sqlalchemy import Integer, String, Date, Time, Text, Enum, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Citas(Base):
    __tablename__ = "Citas"

    idCita: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idPaciente: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    idProfesional: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora: Mapped[time] = mapped_column(Time, nullable=False)
    tipoCita: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tipoSesion: Mapped[str | None] = mapped_column(String(80), nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str | None] = mapped_column(Enum("Pendiente", "Completada", "Cancelada"), default="Pendiente")
    creado_por_profesional: Mapped[bool | None] = mapped_column(Boolean, default=False)
    motivoCancelacion: Mapped[str | None] = mapped_column(Text, nullable=True)

    paciente = relationship("Register", back_populates="citas_paciente", foreign_keys=[idPaciente])
    profesional = relationship("Register", back_populates="citas_profesional", foreign_keys=[idProfesional])

    def to_dict(self):
        return {
            "idCita": self.idCita,
            "idPaciente": self.idPaciente,
            "idProfesional": self.idProfesional,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "hora": self.hora.strftime("%H:%M") if self.hora else None,
            "tipoCita": self.tipoCita,
            "tipoSesion": self.tipoSesion,
            "motivo": self.motivo,
            "notas": self.notas,
            "estado": self.estado,
            "creado_por_profesional": self.creado_por_profesional,
            "motivoCancelacion": self.motivoCancelacion,
        }
