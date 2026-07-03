from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, String, Enum, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Facturas(Base):
    __tablename__ = "Facturas"

    idFactura: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idPaciente: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    idProfesional: Mapped[int] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="CASCADE"), nullable=False)
    idCita: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monto: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    metodoPago: Mapped[str | None] = mapped_column(Enum("banco", "tarjeta", "efectivo", "transferencia", "pse"), default="tarjeta")
    estadoPago: Mapped[str | None] = mapped_column(Enum("Pendiente", "Parcial", "Pagado", "Cancelado"), default="Pendiente")
    fecha: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    anulada: Mapped[bool | None] = mapped_column(Boolean, default=False)
    motivoAnulacion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referenciaPago: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idTransaccionPago: Mapped[str | None] = mapped_column(String(64), nullable=True)

    paciente = relationship("Register", back_populates="facturas_paciente", foreign_keys=[idPaciente])
    profesional = relationship("Register", back_populates="facturas_profesional", foreign_keys=[idProfesional])
    items = relationship("ItemsFactura", back_populates="factura", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "idFactura": self.idFactura,
            "idPaciente": self.idPaciente,
            "idProfesional": self.idProfesional,
            "idCita": self.idCita,
            "monto": float(self.monto) if self.monto else None,
            "metodoPago": self.metodoPago,
            "estadoPago": self.estadoPago,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "anulada": self.anulada,
            "motivoAnulacion": self.motivoAnulacion,
            "referenciaPago": self.referenciaPago,
            "idTransaccionPago": self.idTransaccionPago,
            "items": [item.to_dict() for item in self.items] if self.items else [],
        }
