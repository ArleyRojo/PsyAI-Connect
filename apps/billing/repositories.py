from decimal import Decimal
from django.db import transaction
from django.db.models import Q, Prefetch
from django.utils import timezone

from apps.billing.models import Facturas, ItemsFactura
from apps.authentication.models import Register


class InvoiceRepository:
    def create_invoice(self, patient_id, professional_id, cita_id, items,
                       fechaPago=None, metodoPago=None, referencia=None, notas=None,
                       evidencia=None, confirmada_por_id=None):
        from django.utils import timezone
        monto = sum(Decimal(str(item["precioUnitario"])) for item in items)
        factura = Facturas.objects.create(
            idPaciente_id=patient_id,
            idProfesional_id=professional_id,
            idCita=cita_id,
            monto=monto,
            estadoPago="Pagado",
            fechaPago=fechaPago,
            metodoPago=metodoPago,
            referencia=referencia,
            notas=notas,
            evidencia=evidencia,
            confirmada_por_id=confirmada_por_id,
            fecha_confirmacion=timezone.now(),
        )
        for item in items:
            ItemsFactura.objects.create(
                idFactura=factura,
                descripcion=item["descripcion"],
                precioUnitario=Decimal(str(item["precioUnitario"])),
            )
        return factura.idFactura

    def _base_invoice_qs(self):
        return Facturas.objects.select_related(
            "idPaciente", "idProfesional"
        ).prefetch_related(
            Prefetch("items", queryset=ItemsFactura.objects.all())
        )

    def get_invoice_by_id(self, invoice_id):
        try:
            factura = self._base_invoice_qs().get(idFactura=invoice_id)
        except Facturas.DoesNotExist:
            return None
        result = factura.to_dict()
        result["nombrePaciente"] = factura.idPaciente.nombre if factura.idPaciente else None
        result["nombreProfesional"] = factura.idProfesional.nombre if factura.idProfesional else None
        return result

    def list_invoices_by_patient(self, patient_id, estado=None, profesional=None, fecha_desde=None, fecha_hasta=None):
        qs = self._base_invoice_qs().filter(idPaciente_id=patient_id)
        if estado == "Anulada":
            qs = qs.filter(anulada=True)
        elif estado:
            qs = qs.filter(anulada=False, estadoPago=estado)
        if profesional:
            qs = qs.filter(idProfesional__nombre__icontains=profesional)
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__lte=fecha_hasta + " 23:59:59")
        facturas = qs.order_by("-fecha")
        result = []
        for f in facturas:
            d = f.to_dict()
            d["nombreProfesional"] = f.idProfesional.nombre if f.idProfesional else None
            result.append(d)
        return result

    def list_invoices_by_professional(self, professional_id, estado=None, paciente=None, fecha_desde=None, fecha_hasta=None):
        qs = self._base_invoice_qs().filter(idProfesional_id=professional_id)
        if estado == "Anulada":
            qs = qs.filter(anulada=True)
        elif estado:
            qs = qs.filter(anulada=False, estadoPago=estado)
        if paciente:
            qs = qs.filter(idPaciente__nombre__icontains=paciente)
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__lte=fecha_hasta + " 23:59:59")
        facturas = qs.order_by("-fecha")
        result = []
        for f in facturas:
            d = f.to_dict()
            d["nombrePaciente"] = f.idPaciente.nombre if f.idPaciente else None
            result.append(d)
        return result

    def list_all_invoices(self, paciente=None, profesional=None, estado=None, fecha_desde=None, fecha_hasta=None):
        qs = self._base_invoice_qs().all()
        if paciente:
            qs = qs.filter(idPaciente__nombre__icontains=paciente)
        if profesional:
            qs = qs.filter(idProfesional__nombre__icontains=profesional)
        if estado == "Anulada":
            qs = qs.filter(anulada=True)
        elif estado:
            qs = qs.filter(anulada=False, estadoPago=estado)
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__lte=fecha_hasta + " 23:59:59")
        facturas = qs.order_by("-fecha")
        result = []
        for f in facturas:
            d = f.to_dict()
            d["nombrePaciente"] = f.idPaciente.nombre if f.idPaciente else None
            d["nombreProfesional"] = f.idProfesional.nombre if f.idProfesional else None
            result.append(d)
        return result

    def confirmar_pago(self, invoice_id, evidencia=None, confirmada_por=None):
        with transaction.atomic():
            factura = Facturas.objects.select_for_update().filter(idFactura=invoice_id).first()
            if not factura:
                return False
            if factura.anulada or factura.estadoPago == "Pagado":
                return False
            factura.estadoPago = "Pagado"
            factura.fechaPago = timezone.now()
            factura.fecha_confirmacion = timezone.now()
            if evidencia:
                factura.evidencia = evidencia
            if confirmada_por:
                factura.confirmada_por = confirmada_por
            factura.save(update_fields=["estadoPago", "fechaPago", "fecha_confirmacion", "evidencia", "confirmada_por"])
        return True

    def annul_invoice(self, invoice_id, motivo):
        updated = Facturas.objects.filter(idFactura=invoice_id).update(
            anulada=True, motivoAnulacion=motivo
        )
        return updated > 0

    def get_invoice_owner(self, invoice_id):
        try:
            factura = Facturas.objects.get(idFactura=invoice_id)
            return (factura.idPaciente_id, factura.idProfesional_id, factura.anulada)
        except Facturas.DoesNotExist:
            return None

    def get_professional_patients(self, professional_id):
        patients = (
            Register.objects.filter(
                facturas_paciente__idProfesional_id=professional_id,
            )
            .distinct()
            .order_by("nombre")
        )
        return [{"idUsuario": p.idUsuario, "nombre": p.nombre} for p in patients]

    def get_invoice_stats_by_professional(self, professional_id):
        from django.db.models import Sum, Q

        stats = Facturas.objects.filter(
            idProfesional_id=professional_id,
            anulada=False,
        ).aggregate(
            total_pagado=Sum(
                "monto", filter=Q(estadoPago="Pagado")
            ),
            total_pendiente=Sum(
                "monto", filter=Q(estadoPago="Pendiente")
            ),
            total_general=Sum("monto"),
        )
        return {
            "totalPagado": float(stats["total_pagado"] or 0),
            "totalPendiente": float(stats["total_pendiente"] or 0),
            "totalGeneral": float(stats["total_general"] or 0),
        }

    def get_invoice_stats_by_patient(self, patient_id):
        from django.db.models import Sum, Q

        stats = Facturas.objects.filter(
            idPaciente_id=patient_id,
            anulada=False,
        ).aggregate(
            total_pagado=Sum("monto", filter=Q(estadoPago="Pagado")),
            total_pendiente=Sum(
                "monto", filter=Q(estadoPago="Pendiente")
            ),
            total_general=Sum("monto"),
        )
        return {
            "totalPagado": float(stats["total_pagado"] or 0),
            "totalPendiente": float(stats["total_pendiente"] or 0),
            "totalGeneral": float(stats["total_general"] or 0),
        }

    def get_invoice_stats_all(self):
        from django.db.models import Sum, Q

        base = Facturas.objects.filter(anulada=False)
        stats = base.aggregate(
            total_facturado=Sum("monto"),
            total_pagado=Sum("monto", filter=Q(estadoPago="Pagado")),
            total_pendiente=Sum("monto", filter=Q(estadoPago="Pendiente")),
        )
        anuladas = Facturas.objects.filter(anulada=True).count()
        return {
            "totalFacturado": float(stats["total_facturado"] or 0),
            "totalPagado": float(stats["total_pagado"] or 0),
            "totalPendiente": float(stats["total_pendiente"] or 0),
            "anuladas": anuladas,
        }