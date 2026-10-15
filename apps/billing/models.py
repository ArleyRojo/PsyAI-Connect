import uuid
import os
from django.db import models

from apps.authentication.models import Register


def evidencia_upload_to(instance, filename):
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    return f"evidencias/{instance.idFactura}_{uuid.uuid4().hex}.{ext}"


class Facturas(models.Model):
    ESTADO_PAGO_CHOICES = [
        ("Pendiente", "Pendiente"),
        ("Pagado", "Pagado"),
    ]

    METODO_PAGO_CHOICES = [
        ("Efectivo", "Efectivo"),
        ("Transferencia", "Transferencia"),
        ("Nequi", "Nequi"),
        ("Bre-B", "Bre-B"),
        ("Daviplata", "Daviplata"),
        ("Tarjeta", "Tarjeta"),
        ("Otro", "Otro"),
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
    estadoPago = models.CharField(
        max_length=10,
        choices=ESTADO_PAGO_CHOICES,
        default="Pendiente",
    )
    fecha = models.DateTimeField(auto_now_add=True)
    fechaPago = models.DateTimeField(null=True, blank=True)
    anulada = models.BooleanField(default=False)
    motivoAnulacion = models.CharField(max_length=255, null=True, blank=True)
    # nuevos campos para registro de pago
    metodoPago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, null=True, blank=True)
    referencia = models.CharField(max_length=60, null=True, blank=True)
    notas = models.CharField(max_length=255, null=True, blank=True)
    # evidencia y confirmación
    evidencia = models.FileField(upload_to=evidencia_upload_to, null=True, blank=True)
    confirmada_por = models.ForeignKey(
        Register,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="confirmada_por",
        related_name="facturas_confirmadas",
    )
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "Facturas"
        indexes = [
            models.Index(
                fields=["idPaciente", "fecha"],
                name="idx_facturas_pac_fecha",
            ),
            models.Index(
                fields=["idProfesional", "fecha"],
                name="idx_facturas_prof_fecha",
            ),
            models.Index(
                fields=["idCita"],
                name="idx_facturas_cita",
            ),
        ]

    def __str__(self):
        return f"Factura {self.idFactura}"

    def to_dict(self):
        return {
            "idFactura": self.idFactura,
            "idPaciente": self.idPaciente_id,
            "idProfesional": self.idProfesional_id,
            "idCita": self.idCita,
            "monto": float(self.monto) if self.monto else None,
            "estadoPago": self.estadoPago,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "fechaPago": self.fechaPago.isoformat() if self.fechaPago else None,
            "anulada": self.anulada,
            "motivoAnulacion": self.motivoAnulacion,
            "metodoPago": self.metodoPago,
            "referencia": self.referencia,
            "notas": self.notas,
            "tieneEvidencia": bool(self.evidencia),
            "evidenciaTipo": "pdf" if self.evidencia and self.evidencia.name.lower().endswith(".pdf") else ("imagen" if self.evidencia else None),
            "confirmadaPor": self.confirmada_por_id,
            "nombreConfirmador": self.confirmada_por.nombre if self.confirmada_por else None,
            "fechaConfirmacion": self.fecha_confirmacion.isoformat() if self.fecha_confirmacion else None,
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
