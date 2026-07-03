from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class RecoveryTokens(Base):
    __tablename__ = "RecoveryTokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idUsuario: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool | None] = mapped_column(Boolean, default=False)
    createdAt: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    usuario = relationship("Register", back_populates="recovery_tokens")

    def to_dict(self):
        return {
            "id": self.id,
            "idUsuario": self.idUsuario,
            "token": self.token,
            "expires": self.expires.isoformat() if self.expires else None,
            "used": self.used,
            "createdAt": self.createdAt.isoformat() if self.createdAt else None,
        }
