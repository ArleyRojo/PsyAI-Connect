from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import F, Prefetch, Q, Sum
from django.utils import timezone

from apps.billing.models import Facturas, ItemsFactura
from apps.authentication.models import Register


class InvoiceRepository:
    def _cleanup_invoices(self, patient_id=None, professional_id=None, *, lock=False):
        qs = Facturas.objects.all()
        if patient_id:
            qs = qs.filter(idPaciente_id=patient_id)
        if professional_id:
            qs = qs.filter(idProfesional_id=professional_id)
        if lock:
            qs = qs.select_for_update()
        return qs

    def get_cleanup_summary(self, patient_id=None, professional_id=None):
        qs = self._cleanup_invoices(patient_id, professional_id)
        invoice_ids = list(qs.values_list("idFactura", flat=True))
        total_items = ItemsFactura.objects.filter(idFactura__in=invoice_ids).count()
        evidence = list(qs.exclude(evidencia="").values_list("evidencia", flat=True))
        return len(invoice_ids), total_items, evidence

    def serialize_cleanup_backup(self, patient_id=None, professional_id=None):
        from django.core.serializers import serialize

        qs = self._cleanup_invoices(patient_id, professional_id).select_related(
            "idPaciente", "idProfesional", "confirmada_por"
        ).prefetch_related("items")
        return serialize("json", qs)

    def delete_invoices_for_cleanup(self, patient_id=None, professional_id=None):
        deleted = deleted_files = 0
        errors = []
        with transaction.atomic():
            for factura in self._cleanup_invoices(patient_id, professional_id, lock=True):
                if factura.evidencia and factura.evidencia.name:
                    try:
                        factura.evidencia.delete(save=False)
                        deleted_files += 1
                    except Exception as exc:
                        errors.append((factura.idFactura, str(exc)))
                factura.delete()
                deleted += 1
        return deleted, deleted_files, errors

    def get_invoices_due_for_reminder(self, now, max_notices, first_days, repeat_days):
        return list(
            Facturas.objects.filter(
                estadoPago="Pendiente", anulada=False,
                recordatoriosEnviados__lt=max_notices,
            ).filter(
                Q(recordatoriosEnviados=0, fecha__lte=now - timedelta(days=first_days))
                | Q(recordatoriosEnviados__gt=0, ultimoRecordatorio__lte=now - timedelta(days=repeat_days))
            ).select_related("idPaciente", "idProfesional")
            .prefetch_related("items")
            .order_by("idPaciente_id", "fecha")
        )

    def get_invoice_for_manual_reminder(self, invoice_id):
        return (
            Facturas.objects.filter(idFactura=invoice_id)
            .select_related("idPaciente", "idProfesional")
            .prefetch_related("items")
            .first()
        )

    def increment_reminder_count(self, invoice_ids, now):
        return Facturas.objects.filter(idFactura__in=invoice_ids).update(
            recordatoriosEnviados=F("recordatoriosEnviados") + 1,
            ultimoRecordatorio=now,
        )

    def get_reminder_status(self, invoice_id):
        return Facturas.objects.filter(idFactura=invoice_id).values(
            "recordatoriosEnviados", "ultimoRecordatorio"
        ).first()

    def get_invoice_item_total(self, invoice_id):
        return ItemsFactura.objects.filter(idFactura_id=invoice_id).aggregate(total=Sum("precioUnitario"))["total"]

    def has_active_invoice_for_appointment(self, appointment_id):
        return Facturas.objects.filter(idCita=appointment_id, anulada=False).exists()

    def has_duplicate_invoice(self, patient_id, professional_id, amount, payment_date):
        return Facturas.objects.filter(
            idPaciente_id=patient_id,
            idProfesional_id=professional_id,
            monto=amount,
            fechaPago__date=payment_date,
            anulada=False,
        ).exists()

    def get_invoice_with_payment_relations(self, invoice_id):
        try:
            return Facturas.objects.select_related(
                "idPaciente", "idProfesional", "confirmada_por"
            ).get(idFactura=invoice_id)
        except Facturas.DoesNotExist:
            return None

    def create_invoice(self, patient_id, professional_id, cita_id, items,
                       fechaPago=None, metodoPago=None, referencia=None, notas=None,
                       evidencia=None, confirmada_por_id=None, estadoPago="Pendiente"):
        from django.utils import timezone
        monto = sum(Decimal(str(item["precioUnitario"])) for item in items)
        factura = Facturas.objects.create(
            idPaciente_id=patient_id,
            idProfesional_id=professional_id,
            idCita=cita_id,
            monto=monto,
            estadoPago=estadoPago,
            fechaPago=fechaPago,
            metodoPago=metodoPago,
            referencia=referencia,
            notas=notas,
            evidencia=evidencia,
            confirmada_por_id=confirmada_por_id,
            fecha_confirmacion=timezone.now() if estadoPago == "Pagado" else None,
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

    def list_invoices_by_patient(self, patient_id, estado=None, profesional=None, fecha_desde=None, fecha_hasta=None, tipo_servicio=None):
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
            qs = qs.filter(fecha__lte=fecha_hasta)
        if tipo_servicio:
            qs = qs.filter(items__descripcion__icontains=tipo_servicio)
        facturas = qs.order_by("-fecha").distinct()
        result = []
        for f in facturas:
            d = f.to_dict()
            d["nombreProfesional"] = f.idProfesional.nombre if f.idProfesional else None
            result.append(d)
        return result

    def list_invoices_by_professional(self, professional_id, estado=None, paciente=None, fecha_desde=None, fecha_hasta=None, tipo_servicio=None):
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
            qs = qs.filter(fecha__lte=fecha_hasta)
        if tipo_servicio:
            qs = qs.filter(items__descripcion__icontains=tipo_servicio)
        facturas = qs.order_by("-fecha").distinct()
        result = []
        for f in facturas:
            d = f.to_dict()
            d["nombrePaciente"] = f.idPaciente.nombre if f.idPaciente else None
            result.append(d)
        return result

    def list_all_invoices(self, paciente=None, profesional=None, estado=None, fecha_desde=None, fecha_hasta=None, tipo_servicio=None):
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
            qs = qs.filter(fecha__lte=fecha_hasta)
        if tipo_servicio:
            qs = qs.filter(items__descripcion__icontains=tipo_servicio)
        facturas = qs.order_by("-fecha").distinct()
        result = []
        for f in facturas:
            d = f.to_dict()
            d["nombrePaciente"] = f.idPaciente.nombre if f.idPaciente else None
            d["nombreProfesional"] = f.idProfesional.nombre if f.idProfesional else None
            result.append(d)
        return result

    def confirmar_pago(self, invoice_id, evidencia=None, confirmada_por=None,
                       metodoPago=None, referencia=None, notas=None):
        with transaction.atomic():
            factura = Facturas.objects.select_for_update().filter(idFactura=invoice_id).first()
            if not factura:
                return False
            if factura.anulada or factura.estadoPago == "Pagado":
                return False
            factura.estadoPago = "Pagado"
            factura.fechaPago = timezone.now()
            factura.fecha_confirmacion = timezone.now()
            update_fields = ["estadoPago", "fechaPago", "fecha_confirmacion"]
            if evidencia:
                factura.evidencia = evidencia
                update_fields.append("evidencia")
            if confirmada_por:
                factura.confirmada_por = confirmada_por
                update_fields.append("confirmada_por")
            if metodoPago:
                factura.metodoPago = metodoPago
                update_fields.append("metodoPago")
            if referencia:
                factura.referencia = referencia
                update_fields.append("referencia")
            if notas:
                factura.notas = notas
                update_fields.append("notas")
            factura.save(update_fields=update_fields)
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
