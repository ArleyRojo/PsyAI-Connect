from datetime import datetime
from sqlalchemy import String, Enum, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Register(Base):
    __tablename__ = "Register"

    idUsuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    contrasena: Mapped[str] = mapped_column(String(200), nullable=False)
    rol: Mapped[str] = mapped_column(Enum("paciente", "profesional", "admin"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    estadoCuenta: Mapped[str] = mapped_column(Enum("Activa", "Suspendida"), default="Activa")
    fechaRegistro: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fotoPerfil: Mapped[str | None] = mapped_column(String(255), nullable=True)

    perfil_paciente = relationship("PerfilPaciente", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    perfil_profesional = relationship("PerfilProfesional", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    accesos = relationship("AuditoriaAccesos", back_populates="usuario", cascade="all, delete-orphan")
    logins = relationship("Login", back_populates="usuario", cascade="all, delete-orphan")
    disponibilidad = relationship("Disponibilidad", back_populates="profesional", cascade="all, delete-orphan")
    citas_paciente = relationship("Citas", back_populates="paciente", foreign_keys="Citas.idPaciente", cascade="all, delete-orphan")
    citas_profesional = relationship("Citas", back_populates="profesional", foreign_keys="Citas.idProfesional", cascade="all, delete-orphan")
    conversaciones = relationship("ConversacionesChatbot", back_populates="paciente", cascade="all, delete-orphan")
    evoluciones = relationship("EvolucionPaciente", back_populates="paciente", cascade="all, delete-orphan")
    pacientes_profesional = relationship("PacientesProfesional", back_populates="profesional", foreign_keys="PacientesProfesional.idProfesional", cascade="all, delete-orphan")
    pacientes_asignados = relationship("PacientesProfesional", back_populates="paciente", foreign_keys="PacientesProfesional.idPaciente", cascade="all, delete-orphan")
    notificaciones = relationship("Notificaciones", back_populates="usuario", cascade="all, delete-orphan")
    mensajes_enviados = relationship("MensajesChat", back_populates="emisor", foreign_keys="MensajesChat.idEmisor", cascade="all, delete-orphan")
    mensajes_recibidos = relationship("MensajesChat", back_populates="receptor", foreign_keys="MensajesChat.idReceptor", cascade="all, delete-orphan")
    recovery_tokens = relationship("RecoveryTokens", back_populates="usuario", cascade="all, delete-orphan")
    facturas_paciente = relationship("Facturas", back_populates="paciente", foreign_keys="Facturas.idPaciente", cascade="all, delete-orphan")
    facturas_profesional = relationship("Facturas", back_populates="profesional", foreign_keys="Facturas.idProfesional", cascade="all, delete-orphan")
    documentos_clinicos = relationship("DocumentosClinicos", back_populates="profesional", foreign_keys="DocumentosClinicos.idProfesional", cascade="all, delete-orphan")
    documentos_paciente_prof = relationship("DocumentosClinicos", back_populates="paciente", foreign_keys="DocumentosClinicos.idPaciente", cascade="all, delete-orphan")
    documentos_paciente = relationship("DocumentosPaciente", back_populates="paciente", cascade="all, delete-orphan")
    reportes_profesional = relationship("Reportes", back_populates="profesional", foreign_keys="Reportes.idProfesional", cascade="all, delete-orphan")
    reportes_paciente = relationship("Reportes", back_populates="paciente", foreign_keys="Reportes.idPaciente", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "idUsuario": self.idUsuario,
            "nombre": self.nombre,
            "email": self.email,
            "contrasena": self.contrasena,
            "rol": self.rol,
            "activo": self.activo,
            "estadoCuenta": self.estadoCuenta,
            "fechaRegistro": self.fechaRegistro.isoformat() if self.fechaRegistro else None,
            "fotoPerfil": self.fotoPerfil,
        }
