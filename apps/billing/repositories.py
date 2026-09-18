from django.db.models import Q, Prefetch

from apps.billing.models import Facturas, ItemsFactura
from apps.authentication.models import Register


class InvoiceRepository:
    def create_invoice(self, patient_id, professional_id, cita_id, items, metodo_pago):
        monto = sum(item["precioUnitario"] for item in items)
        factura = Facturas.objects.create(
            idPaciente_id=patient_id,
            idProfesional_id=professional_id,
            idCita=cita_id,
            monto=monto,
            metodoPago=metodo_pago,
            estadoPago="Pendiente",
        )
        for item in items:
            ItemsFactura.objects.create(
                idFactura=factura,
                descripcion=item["descripcion"],
                precioUnitario=item["precioUnitario"],
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

    def list_invoices_by_patient(self, patient_id):
        facturas = self._base_invoice_qs().filter(
            idPaciente_id=patient_id
        ).order_by("-fecha")
        result = []
        for f in facturas:
            d = f.to_dict()
            d["nombreProfesional"] = f.idProfesional.nombre if f.idProfesional else None
            result.append(d)
        return result

    def list_invoices_by_professional(self, professional_id, estado=None, fecha_desde=None, fecha_hasta=None):
        qs = self._base_invoice_qs().filter(idProfesional_id=professional_id)
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
            result.append(d)
        return result

    def list_all_invoices(self, paciente=None, profesional=None, estado=None, metodo_pago=None, fecha_desde=None, fecha_hasta=None):
        qs = self._base_invoice_qs().all()
        if paciente:
            qs = qs.filter(idPaciente__nombre__icontains=paciente)
        if estado == "Anulada":
            qs = qs.filter(anulada=True)
        elif estado:
            qs = qs.filter(anulada=False, estadoPago=estado)
        if metodo_pago:
            qs = qs.filter(metodoPago=metodo_pago)
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

    def update_payment_status(self, invoice_id, nuevo_estado):
        updated = Facturas.objects.filter(idFactura=invoice_id).update(estadoPago=nuevo_estado)
        return updated > 0

    def annul_invoice(self, invoice_id, motivo):
        updated = Facturas.objects.filter(idFactura=invoice_id).update(anulada=True, motivoAnulacion=motivo)
        return updated > 0

    def set_payment_reference(self, invoice_id, referencia, id_transaccion):
        updated = Facturas.objects.filter(idFactura=invoice_id).update(
            referenciaPago=referencia, idTransaccionPago=id_transaccion,
        )
        return updated > 0

    def get_invoice_by_reference(self, reference):
        try:
            factura = Facturas.objects.get(referenciaPago=reference)
            return factura.idFactura
        except Facturas.DoesNotExist:
            return None

    def get_invoice_owner(self, invoice_id):
        try:
            factura = Facturas.objects.get(idFactura=invoice_id)
            return (factura.idPaciente_id, factura.idProfesional_id, factura.anulada)
        except Facturas.DoesNotExist:
            return None

    def get_invoice_model(self, invoice_id):
        try:
            return self._base_invoice_qs().get(idFactura=invoice_id)
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
        from django.db.models import Sum, Case, When, Value, Count, Q, F

        stats = Facturas.objects.filter(
            idProfesional_id=professional_id,
            anulada=False,
        ).aggregate(
            total_pagado=Sum(
                "monto", filter=Q(estadoPago="Pagado")
            ),
            total_pendiente=Sum(
                "monto", filter=Q(estadoPago__in=("Pendiente", "Parcial"))
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
            total_pendiente=Sum("monto", filter=Q(estadoPago__in=("Pendiente", "Parcial"))),
        )
        anuladas = Facturas.objects.filter(anulada=True).count()
        return {
            "totalFacturado": float(stats["total_facturado"] or 0),
            "totalPagado": float(stats["total_pagado"] or 0),
            "totalPendiente": float(stats["total_pendiente"] or 0),
            "anuladas": anuladas,
        }
