from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ConversacionesChatbot(Base):
    __tablename__ = "ConversacionesChatbot"

    idConversacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idPaciente: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    mensajeUsuario: Mapped[str | None] = mapped_column(Text, nullable=True)
    respuestaChatbot: Mapped[str | None] = mapped_column(Text, nullable=True)
    nivelEmocionalDetectado: Mapped[str | None] = mapped_column(String(50), nullable=True)
    palabrasRiesgoDetectadas: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    paciente = relationship("Register", back_populates="conversaciones")

    def to_dict(self):
        return {
            "idConversacion": self.idConversacion,
            "idPaciente": self.idPaciente,
            "mensajeUsuario": self.mensajeUsuario,
            "respuestaChatbot": self.respuestaChatbot,
            "nivelEmocionalDetectado": self.nivelEmocionalDetectado,
            "palabrasRiesgoDetectadas": self.palabrasRiesgoDetectadas,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }
