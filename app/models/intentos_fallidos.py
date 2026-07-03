from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class IntentosFallidos(Base):
    __tablename__ = "intentos_fallidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ultimo_intento: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "intentos": self.intentos,
            "ultimo_intento": self.ultimo_intento.isoformat() if self.ultimo_intento else None,
            "bloqueado_hasta": self.bloqueado_hasta.isoformat() if self.bloqueado_hasta else None,
        }
