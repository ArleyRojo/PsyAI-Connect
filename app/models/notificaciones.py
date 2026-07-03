from datetime import datetime
from sqlalchemy import Integer, String, Text, Enum, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Notificaciones(Base):
    __tablename__ = "Notificaciones"

    idNotificacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idUsuario: Mapped[int | None] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="SET NULL"), nullable=True)
    rol: Mapped[str | None] = mapped_column(Enum("admin", "profesional", "paciente"), nullable=True)
    titulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    destinatario: Mapped[str | None] = mapped_column(String(80), nullable=True)
    email_individual: Mapped[str | None] = mapped_column(String(120), nullable=True)
    enviado_por: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estado: Mapped[str | None] = mapped_column(Enum("enviado", "pendiente"), default="enviado")
    leido: Mapped[bool | None] = mapped_column(Boolean, default=False)
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    fecha_programada: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    usuario = relationship("Register", back_populates="notificaciones")

    def to_dict(self):
        return {
            "idNotificacion": self.idNotificacion,
            "idUsuario": self.idUsuario,
            "rol": self.rol,
            "titulo": self.titulo,
            "mensaje": self.mensaje,
            "tipo": self.tipo,
            "destinatario": self.destinatario,
            "email_individual": self.email_individual,
            "enviado_por": self.enviado_por,
            "estado": self.estado,
            "leido": self.leido,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "fecha_programada": self.fecha_programada.isoformat() if self.fecha_programada else None,
        }
