from datetime import date, time
from sqlalchemy import Integer, Date, Time, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Disponibilidad(Base):
    __tablename__ = "Disponibilidad"

    idDisponibilidad: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idProfesional: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    estado: Mapped[str | None] = mapped_column(Enum("Disponible", "Bloqueado", "Ocupado"), default="Disponible")

    profesional = relationship("Register", back_populates="disponibilidad")

    def to_dict(self):
        return {
            "idDisponibilidad": self.idDisponibilidad,
            "idProfesional": self.idProfesional,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "hora_inicio": self.hora_inicio.strftime("%H:%M") if self.hora_inicio else None,
            "hora_fin": self.hora_fin.strftime("%H:%M") if self.hora_fin else None,
            "estado": self.estado,
        }
