from decimal import Decimal
from sqlalchemy import Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ItemsFactura(Base):
    __tablename__ = "ItemsFactura"

    idItem: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idFactura: Mapped[int] = mapped_column(Integer, ForeignKey("Facturas.idFactura", ondelete="CASCADE"), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    precioUnitario: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    factura = relationship("Facturas", back_populates="items")

    def to_dict(self):
        return {
            "idItem": self.idItem,
            "idFactura": self.idFactura,
            "descripcion": self.descripcion,
            "precioUnitario": float(self.precioUnitario) if self.precioUnitario else None,
        }
