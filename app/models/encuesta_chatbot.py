from datetime import datetime
from sqlalchemy import Integer, String, Text, Boolean, Enum, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class EncuestaChatbot(Base):
    __tablename__ = "EncuestaChatbot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idPaciente: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    utilidad: Mapped[bool] = mapped_column(Boolean, nullable=False)
    claridad: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recomendaria: Mapped[str] = mapped_column(Enum("si", "no"), nullable=False)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "idPaciente": self.idPaciente,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "utilidad": self.utilidad,
            "claridad": self.claridad,
            "recomendaria": self.recomendaria,
            "comentario": self.comentario,
        }
