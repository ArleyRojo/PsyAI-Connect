from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class PerfilPaciente(Base):
    __tablename__ = "PerfilPaciente"

    idPaciente: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), primary_key=True)
    genero: Mapped[str | None] = mapped_column(String(20), nullable=True)
    edad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numeroTelefonico: Mapped[str | None] = mapped_column(String(20), nullable=True)
    consentimientoDatos: Mapped[bool | None] = mapped_column(Boolean, default=False)
    consentimiento_chatbot: Mapped[bool | None] = mapped_column(Boolean, default=False)

    usuario = relationship("Register", back_populates="perfil_paciente")

    def to_dict(self):
        return {
            "idPaciente": self.idPaciente,
            "genero": self.genero,
            "edad": self.edad,
            "numeroTelefonico": self.numeroTelefonico,
            "consentimientoDatos": self.consentimientoDatos,
            "consentimiento_chatbot": self.consentimiento_chatbot,
        }
