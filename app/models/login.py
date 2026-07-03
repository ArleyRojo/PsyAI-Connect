from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Login(Base):
    __tablename__ = "Login"

    idLogin: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idUsuario: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False)
    contrasena: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ultimoAcceso: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    usuario = relationship("Register", back_populates="logins")

    def to_dict(self):
        return {
            "idLogin": self.idLogin,
            "idUsuario": self.idUsuario,
            "email": self.email,
            "ultimoAcceso": self.ultimoAcceso.isoformat() if self.ultimoAcceso else None,
        }
