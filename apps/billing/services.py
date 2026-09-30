import hashlib
import uuid
import logging

import requests
from django.conf import settings
from django.template.loader import render_to_string

from apps.billing.repositories import InvoiceRepository

logger = logging.getLogger(__name__)

METODOS_PAGO_SIMULADO = {"pse", "tarjeta"}

METODO_PAGO_LABELS = {
    "banco": "Banco",
    "tarjeta": "Tarjeta",
    "efectivo": "Efectivo",
    "transferencia": "Transferencia",
    "pse": "PSE",
}


class InvoiceMailService:
    @staticmethod
    def _get_site_url():
        return getattr(settings, "SITE_URL", "http://localhost:8000")

    @staticmethod
    def _formatear_fecha(fecha):
        if fecha and hasattr(fecha, "strftime"):
            return fecha.strftime("%d/%m/%Y %H:%M")
        return str(fecha) if fecha else ""

    @classmethod
    def send_factura_notificacion(cls, recipient_email, *, titulo, mensaje, id_factura,
                                  nombre_paciente=None, nombre_profesional=None,
                                  monto=0, metodo_pago="tarjeta", estado_pago="Pendiente",
                                  fecha=None, items=None, motivo_anulacion=None,
                                  cta_link=None, cta_texto=None):
        if not recipient_email:
            logger.warning("No se envió correo de factura: destinatario vacío")
            return

        site_url = cls._get_site_url()
        ctx = {
            "titulo": titulo,
            "mensaje": mensaje,
            "id_factura": id_factura,
            "fecha": cls._formatear_fecha(fecha) if fecha else "",
            "nombre_paciente": nombre_paciente,
            "nombre_profesional": nombre_profesional,
            "metodo_pago": METODO_PAGO_LABELS.get(metodo_pago, metodo_pago),
            "estado_pago": estado_pago,
            "monto_total": f"{float(monto):,.0f}" if monto else "0",
            "items": items or [],
            "motivo_anulacion": motivo_anulacion,
            "cta_link": cta_link,
            "cta_texto": cta_texto or "Ver factura",
            "site_url": site_url,
        }

        try:
            subject = titulo
            text_body = f"{titulo}\n\n{mensaje}\n\nFactura #{id_factura}\nTotal: ${float(monto):,.0f}\nEstado: {estado_pago}"
            html_body = render_to_string("emails/factura_notificacion.html", ctx)

            from django.core.mail import EmailMultiAlternatives
            msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [recipient_email])
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=True)
            logger.info(f"Correo de factura enviado a {recipient_email}: {titulo}")
        except Exception as e:
            logger.error(f"Error enviando correo de factura a {recipient_email}: {e}")


class InvoiceService:
    def __init__(self):
        self.repo = InvoiceRepository()

    @staticmethod
    def estado_factura_agendada(metodo_pago):
        return "Pagado" if metodo_pago in METODOS_PAGO_SIMULADO else "Pendiente"

    def create_invoice(self, patient_id, professional_id, data):
        cita_id = data.get("idCita")
        items = data.get("items", [])
        metodo_pago = data.get("metodoPago", "tarjeta")

        if not items or not isinstance(items, list):
            return {"success": False, "message": "Debes incluir al menos un item"}, 400
        if metodo_pago not in ("banco", "tarjeta"):
            return {"success": False, "message": "Método de pago inválido"}, 400
        if any(not item.get("descripcion") or not item.get("precioUnitario") for item in items):
            return {"success": False, "message": "Cada item debe tener descripción y precio unitario"}, 400

        try:
            invoice_id = self.repo.create_invoice(
                patient_id, professional_id, cita_id, items, metodo_pago,
            )

            try:
                from apps.authentication.models import Register
                paciente = Register.objects.filter(idUsuario=patient_id).first()
                profesional = Register.objects.filter(idUsuario=professional_id).first()
                site_url = InvoiceMailService._get_site_url()
                InvoiceMailService.send_factura_notificacion(
                    recipient_email=paciente.email if paciente else None,
                    titulo="Nueva factura generada",
                    mensaje=f"Se ha generado una factura por un valor de ${sum(i['precioUnitario'] for i in items):,.0f}.",
                    id_factura=invoice_id,
                    nombre_paciente=paciente.nombre if paciente else None,
                    nombre_profesional=profesional.nombre if profesional else None,
                    monto=sum(i["precioUnitario"] for i in items),
                    metodo_pago=metodo_pago,
                    estado_pago="Pendiente",
                    items=[{"descripcion": i["descripcion"], "precio": f"{i['precioUnitario']:,.0f}"} for i in items],
                    cta_link=f"{site_url}/aside-patient/facturas.html",
                )
            except Exception as e:
                logger.error(f"Error enviando correo de factura: {e}")

            return {"success": True, "message": "Factura creada correctamente", "idFactura": invoice_id}, 201
        except Exception as e:
            logger.error("Error creando factura: %s", e, exc_info=True)
            return {"success": False, "message": "Error al crear la factura"}, 500

    def get_invoice(self, invoice_id, user_id, user_role):
        factura = self.repo.get_invoice_by_id(invoice_id)
        if not factura:
            return {"success": False, "message": "Factura no encontrada"}, 404

        if user_role not in ("admin",) and factura["idPaciente"] != user_id and factura["idProfesional"] != user_id:
            return {"success": False, "message": "No tienes permiso para ver esta factura"}, 403

        if factura.get("fecha"):
            factura["fecha"] = factura["fecha"].strftime("%d/%m/%Y %H:%M") if hasattr(factura["fecha"], "strftime") else str(factura["fecha"])
        if factura.get("monto"):
            factura["monto"] = float(factura["monto"])
        for item in factura.get("items", []):
            if item.get("precioUnitario"):
                item["precioUnitario"] = float(item["precioUnitario"])

        return {"success": True, "factura": factura}, 200

    def list_patient_invoices(self, patient_id):
        facturas = self.repo.list_invoices_by_patient(patient_id)
        for f in facturas:
            if f.get("fecha"):
                f["fecha"] = f["fecha"].strftime("%d/%m/%Y %H:%M") if hasattr(f["fecha"], "strftime") else str(f["fecha"])
            if f.get("monto"):
                f["monto"] = float(f["monto"])
            for item in f.get("items", []):
                if item.get("precioUnitario"):
                    item["precioUnitario"] = float(item["precioUnitario"])
        return {"success": True, "facturas": facturas}, 200

    def list_professional_invoices(self, professional_id, estado=None, fecha_desde=None, fecha_hasta=None):
        facturas = self.repo.list_invoices_by_professional(
            professional_id, estado=estado, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )
        for f in facturas:
            if f.get("fecha"):
                f["fecha"] = f["fecha"].strftime("%d/%m/%Y %H:%M") if hasattr(f["fecha"], "strftime") else str(f["fecha"])
            if f.get("monto"):
                f["monto"] = float(f["monto"])
        return {"success": True, "facturas": facturas}, 200

    def list_all_invoices(self, paciente=None, profesional=None, estado=None, metodo_pago=None, fecha_desde=None, fecha_hasta=None):
        facturas = self.repo.list_all_invoices(
            paciente=paciente, profesional=profesional, estado=estado,
            metodo_pago=metodo_pago, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )
        for f in facturas:
            if f.get("fecha"):
                f["fecha"] = f["fecha"].strftime("%d/%m/%Y %H:%M") if hasattr(f["fecha"], "strftime") else str(f["fecha"])
            if f.get("monto"):
                f["monto"] = float(f["monto"])
        return {"success": True, "facturas": facturas}, 200

    def update_status(self, invoice_id, nuevo_estado, user_id, user_role):
        if nuevo_estado not in ("Pendiente", "Parcial", "Pagado", "Cancelado"):
            return {"success": False, "message": "Estado de pago inválido"}, 400

        row = self.repo.get_invoice_owner(invoice_id)
        if not row:
            return {"success": False, "message": "Factura no encontrada"}, 404

        if row[2]:
            return {"success": False, "message": "No se puede cambiar el estado de una factura anulada"}, 400

        if user_role not in ("admin",) and row[1] != user_id:
            return {"success": False, "message": "No tienes permiso para modificar esta factura"}, 403

        self.repo.update_payment_status(invoice_id, nuevo_estado)
        return {"success": True, "message": f"Estado actualizado a {nuevo_estado}"}, 200

    def cancel_payment(self, invoice_id, patient_id):
        factura = self.repo.get_invoice_by_id(invoice_id)
        if not factura:
            return {"success": False, "message": "Factura no encontrada"}, 404
        if factura["idPaciente"] != patient_id:
            return {"success": False, "message": "Esta factura no te pertenece"}, 403
        if factura["anulada"]:
            return {"success": False, "message": "La factura ya está anulada"}, 400
        if factura["estadoPago"] == "Pagado":
            return {"success": False, "message": "La factura ya está pagada"}, 400

        self.repo.update_payment_status(invoice_id, "Cancelado")
        return {"success": True, "message": "Pago cancelado"}, 200

    def annul_invoice(self, invoice_id, motivo, user_id, user_role):
        if not motivo or not motivo.strip():
            return {"success": False, "message": "Debes indicar el motivo de anulación"}, 400

        row = self.repo.get_invoice_owner(invoice_id)
        if not row:
            return {"success": False, "message": "Factura no encontrada"}, 404

        if row[2]:
            return {"success": False, "message": "La factura ya está anulada"}, 400

        if user_role not in ("admin",) and row[1] != user_id:
            return {"success": False, "message": "No tienes permiso para anular esta factura"}, 403

        self.repo.annul_invoice(invoice_id, motivo.strip())

        try:
            from apps.authentication.models import Register
            factura_data = self.repo.get_invoice_by_id(invoice_id)
            if factura_data:
                paciente = Register.objects.filter(idUsuario=factura_data["idPaciente"]).first()
                profesional = Register.objects.filter(idUsuario=factura_data["idProfesional"]).first()
                site_url = InvoiceMailService._get_site_url()
                for recipient in [paciente, profesional]:
                    if recipient:
                        InvoiceMailService.send_factura_notificacion(
                            recipient_email=recipient.email,
                            titulo="Factura anulada",
                            mensaje=f"La factura #{invoice_id} ha sido anulada.",
                            id_factura=invoice_id,
                            nombre_paciente=paciente.nombre if paciente else None,
                            nombre_profesional=profesional.nombre if profesional else None,
                            monto=factura_data.get("monto", 0),
                            metodo_pago=factura_data.get("metodoPago", "tarjeta"),
                            estado_pago="Anulada",
                            motivo_anulacion=motivo.strip(),
                            cta_link=f"{site_url}/aside-patient/facturas.html",
                        )
        except Exception as e:
            logger.error(f"Error enviando correo de anulación: {e}")

        return {"success": True, "message": "Factura anulada correctamente"}, 200

    def init_wompi_payment(self, invoice_id, patient_id):
        factura = self.repo.get_invoice_by_id(invoice_id)
        if not factura:
            return {"success": False, "message": "Factura no encontrada"}, 404

        if factura["idPaciente"] != patient_id:
            return {"success": False, "message": "Esta factura no te pertenece"}, 403

        if factura["anulada"]:
            return {"success": False, "message": "No se puede pagar una factura anulada"}, 400

        if factura["estadoPago"] == "Pagado":
            return {"success": False, "message": "Esta factura ya está pagada"}, 400

        public_key = settings.WOMPI_PUBLIC_KEY
        integrity_secret = settings.WOMPI_INTEGRITY_SECRET
        if not public_key or not integrity_secret:
            return {"success": False, "message": "Pasarela de pago no configurada"}, 500

        monto = float(factura["monto"])
        amount_in_cents = int(round(monto * 100))
        reference = f"PSYAI-{invoice_id}-{uuid.uuid4().hex[:8].upper()}"

        raw = f"{reference}{amount_in_cents}COP{integrity_secret}"
        integrity_hash = hashlib.sha256(raw.encode()).hexdigest()

        self.repo.set_payment_reference(invoice_id, reference, None)

        is_sandbox = public_key.startswith("pub_test_")

        return {
            "success": True,
            "data": {
                "publicKey": public_key,
                "currency": "COP",
                "amountInCents": amount_in_cents,
                "reference": reference,
                "signature": {"integrity": integrity_hash},
                "idFactura": invoice_id,
                "sandbox": is_sandbox,
            },
        }, 200

    def get_patient_invoice_stats(self, patient_id):
        stats = self.repo.get_invoice_stats_by_patient(patient_id)
        return {"success": True, "stats": stats}, 200

    def get_admin_stats(self):
        stats = self.repo.get_invoice_stats_all()
        return {"success": True, "stats": stats}, 200

    def get_professional_patients(self, professional_id):
        patients = self.repo.get_professional_patients(professional_id)
        return {"success": True, "pacientes": patients}, 200

    def confirm_wompi_payment(self, invoice_id, transaction_id, patient_id):
        factura = self.repo.get_invoice_by_id(invoice_id)
        if not factura:
            return {"success": False, "message": "Factura no encontrada"}, 404

        if factura["idPaciente"] != patient_id:
            return {"success": False, "message": "Esta factura no te pertenece"}, 403

        if factura["estadoPago"] == "Pagado":
            return {"success": True, "message": "La factura ya estaba marcada como pagada"}, 200

        public_key = settings.WOMPI_PUBLIC_KEY or ""
        base_url = (
            "https://sandbox.wompi.co/v1"
            if public_key.startswith("pub_test")
            else "https://production.wompi.co/v1"
        )

        try:
            headers = {"Authorization": f"Bearer {public_key}"}
            resp = requests.get(
                f"{base_url}/transactions/{transaction_id}",
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            transaction = resp.json().get("data", {})
        except Exception as e:
            logger.error("Error verificando transacción Wompi: %s", e, exc_info=True)
            return {"success": False, "message": "No se pudo verificar el pago con Wompi. Intenta más tarde."}, 502

        if transaction.get("status") != "APPROVED":
            return {"success": False, "message": f"La transacción no está aprobada (estado: {transaction.get('status')})"}, 400

        reference = transaction.get("reference", "")
        if reference != factura.get("referenciaPago"):
            logger.warning(
                "Referencia de transacción no coincide con la factura %s (esperado=%s, recibido=%s)",
                invoice_id, factura.get("referenciaPago"), reference,
            )
            return {"success": False, "message": "La transacción no corresponde a esta factura"}, 400

        self.repo.update_payment_status(invoice_id, "Pagado")
        self.repo.set_payment_reference(invoice_id, reference, transaction_id)

        try:
            from apps.authentication.models import Register
            paciente = Register.objects.filter(idUsuario=patient_id).first()
            factura_data = self.repo.get_invoice_by_id(invoice_id)
            if factura_data:
                profesional = Register.objects.filter(idUsuario=factura_data["idProfesional"]).first()
                site_url = InvoiceMailService._get_site_url()
                InvoiceMailService.send_factura_notificacion(
                    recipient_email=paciente.email if paciente else None,
                    titulo="Pago confirmado",
                    mensaje=f"Tu pago de la factura #{invoice_id} ha sido confirmado correctamente.",
                    id_factura=invoice_id,
                    nombre_paciente=paciente.nombre if paciente else None,
                    nombre_profesional=profesional.nombre if profesional else None,
                    monto=factura_data.get("monto", 0),
                    metodo_pago=factura_data.get("metodoPago", "tarjeta"),
                    estado_pago="Pagado",
                    cta_link=f"{site_url}/aside-patient/facturas.html",
                )
                InvoiceMailService.send_factura_notificacion(
                    recipient_email=profesional.email if profesional else None,
                    titulo="Pago recibido",
                    mensaje=f"El paciente {paciente.nombre if paciente else ''} ha realizado el pago de la factura #{invoice_id}.",
                    id_factura=invoice_id,
                    nombre_paciente=paciente.nombre if paciente else None,
                    nombre_profesional=profesional.nombre if profesional else None,
                    monto=factura_data.get("monto", 0),
                    metodo_pago=factura_data.get("metodoPago", "tarjeta"),
                    estado_pago="Pagado",
                    cta_link=f"{site_url}/aside-professional/facturacion.html",
                )
        except Exception as e:
            logger.error(f"Error enviando correo de pago confirmado: {e}")

        return {"success": True, "message": "Pago confirmado correctamente"}, 200
