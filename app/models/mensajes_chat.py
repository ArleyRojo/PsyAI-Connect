from datetime import datetime
from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class MensajesChat(Base):
    __tablename__ = "MensajesChat"

    idMensaje: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idEmisor: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    idReceptor: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    leido: Mapped[bool | None] = mapped_column(Boolean, default=False)
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    emisor = relationship("Register", back_populates="mensajes_enviados", foreign_keys=[idEmisor])
    receptor = relationship("Register", back_populates="mensajes_recibidos", foreign_keys=[idReceptor])

    def to_dict(self):
        return {
            "idMensaje": self.idMensaje,
            "idEmisor": self.idEmisor,
            "idReceptor": self.idReceptor,
            "mensaje": self.mensaje,
            "leido": self.leido,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }
