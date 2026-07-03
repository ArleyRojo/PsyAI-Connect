from sqlalchemy import Integer, String, Text, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class PerfilProfesional(Base):
    __tablename__ = "PerfilProfesional"

    idProfesional: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), primary_key=True)
    genero: Mapped[str | None] = mapped_column(String(20), nullable=True)
    edad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    especialidad: Mapped[str | None] = mapped_column(String(120), nullable=True)
    licencia: Mapped[str | None] = mapped_column(String(120), nullable=True)
    experiencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str | None] = mapped_column(Enum("Activo", "Inactivo"), default="Activo")

    usuario = relationship("Register", back_populates="perfil_profesional")

    def to_dict(self):
        return {
            "idProfesional": self.idProfesional,
            "genero": self.genero,
            "edad": self.edad,
            "especialidad": self.especialidad,
            "licencia": self.licencia,
            "experiencia": self.experiencia,
            "estado": self.estado,
        }
