from django.db import models

from apps.authentication.models import Register


class Facturas(models.Model):
    METODO_PAGO_CHOICES = [
        ("banco", "Banco"),
        ("tarjeta", "Tarjeta"),
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia"),
        ("pse", "PSE"),
    ]
    ESTADO_PAGO_CHOICES = [
        ("Pendiente", "Pendiente"),
        ("Parcial", "Parcial"),
        ("Pagado", "Pagado"),
        ("Cancelado", "Cancelado"),
    ]

    idFactura = models.AutoField(primary_key=True)
    idPaciente = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
        related_name="facturas_paciente",
    )
    idProfesional = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idProfesional",
        related_name="facturas_profesional",
    )
    idCita = models.IntegerField(null=True, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    metodoPago = models.CharField(
        max_length=15,
        choices=METODO_PAGO_CHOICES,
        default="tarjeta",
    )
    estadoPago = models.CharField(
        max_length=10,
        choices=ESTADO_PAGO_CHOICES,
        default="Pendiente",
    )
    fecha = models.DateTimeField(auto_now_add=True)
    anulada = models.BooleanField(default=False)
    motivoAnulacion = models.CharField(max_length=255, null=True, blank=True)
    referenciaPago = models.CharField(max_length=64, null=True, blank=True)
    idTransaccionPago = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = "Facturas"

    def __str__(self):
        return f"Factura {self.idFactura}"

    def to_dict(self):
        return {
            "idFactura": self.idFactura,
            "idPaciente": self.idPaciente_id,
            "idProfesional": self.idProfesional_id,
            "idCita": self.idCita,
            "monto": float(self.monto) if self.monto else None,
            "metodoPago": self.metodoPago,
            "estadoPago": self.estadoPago,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "anulada": self.anulada,
            "motivoAnulacion": self.motivoAnulacion,
            "referenciaPago": self.referenciaPago,
            "idTransaccionPago": self.idTransaccionPago,
            "items": [item.to_dict() for item in self.items.all()],
        }


class ItemsFactura(models.Model):
    idItem = models.AutoField(primary_key=True)
    idFactura = models.ForeignKey(
        Facturas,
        on_delete=models.CASCADE,
        db_column="idFactura",
        related_name="items",
    )
    descripcion = models.CharField(max_length=120, null=True, blank=True)
    precioUnitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "ItemsFactura"

    def __str__(self):
        return self.descripcion or f"Item {self.idItem}"

    def to_dict(self):
        return {
            "idItem": self.idItem,
            "idFactura": self.idFactura_id,
            "descripcion": self.descripcion,
            "precioUnitario": float(self.precioUnitario) if self.precioUnitario else None,
        }
