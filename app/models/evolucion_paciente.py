from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class EvolucionPaciente(Base):
    __tablename__ = "EvolucionPaciente"

    idEvolucion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idPaciente: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    idConversacion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estadoEmocional: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nivelEnergia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notasPersonales: Mapped[str | None] = mapped_column(Text, nullable=True)
    resultadoEmocional: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    paciente = relationship("Register", back_populates="evoluciones")

    def to_dict(self):
        return {
            "idEvolucion": self.idEvolucion,
            "idPaciente": self.idPaciente,
            "idConversacion": self.idConversacion,
            "estadoEmocional": self.estadoEmocional,
            "nivelEnergia": self.nivelEnergia,
            "notasPersonales": self.notasPersonales,
            "resultadoEmocional": self.resultadoEmocional,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }
