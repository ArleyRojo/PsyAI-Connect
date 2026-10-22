import logging
from decimal import Decimal
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from apps.billing.repositories import InvoiceRepository
from apps.billing.models import Facturas

logger = logging.getLogger(__name__)


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
                                   monto=0, estado_pago="Pendiente",
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

    def create_invoice(self, professional_user_id, patient_id, cita_id, items,
                       fechaPago, metodoPago, referencia, notas, evidencia):
        # Validaciones de items ya hechas en la vista
        # Validar relación profesional-paciente
        from apps.professionals.models import PacientesProfesional
        if not PacientesProfesional.objects.filter(idProfesional_id=professional_user_id, idPaciente_id=patient_id).exists():
            return {"success": False, "message": "No tienes relación profesional-paciente para facturar a este paciente"}, 403

        # Validar fechaPago no futura
        from django.utils import timezone
        try:
            fechaPago_dt = timezone.datetime.fromisoformat(fechaPago) if isinstance(fechaPago, str) else fechaPago
        except Exception:
            return {"success": False, "message": "Formato de fechaPago inválido"}, 400
        if fechaPago_dt and fechaPago_dt.date() > timezone.now().date():
            return {"success": False, "message": "La fecha del pago no puede ser futura"}, 400

        # Validar metodoPago
        allowed_methods = dict(Facturas.METODO_PAGO_CHOICES).keys()
        if metodoPago not in allowed_methods:
            return {"success": False, "message": "Método de pago inválido"}, 400

        # Validar evidencia obligatoria
        if not evidencia:
            return {"success": False, "message": "Debes adjuntar la evidencia del pago"}, 400
        from apps.core.utils import validate_file_upload
        allowed_ext = ["jpg", "jpeg", "png", "webp", "pdf"]
        name, error = validate_file_upload(evidencia, allowed_extensions=allowed_ext)
        if error:
            return {"success": False, "message": f"Evidencia inválida: {error}"}, 400

        try:
            invoice_id = self.repo.create_invoice(
                patient_id, professional_user_id, cita_id, items,
                fechaPago=fechaPago_dt,
                metodoPago=metodoPago,
                referencia=referencia,
                notas=notas,
                evidencia=evidencia,
                confirmada_por_id=professional_user_id,
                estadoPago="Pagado",
            )

            # enviar correo al paciente
            try:
                from apps.authentication.models import Register
                paciente = Register.objects.filter(idUsuario=patient_id).first()
                profesional = Register.objects.filter(idUsuario=professional_user_id).first()
                site_url = InvoiceMailService._get_site_url()
                InvoiceMailService.send_factura_notificacion(
                    recipient_email=paciente.email if paciente else None,
                    titulo="Pago registrado",
                    mensaje=f"Se ha registrado un pago por ${sum(Decimal(str(i['precioUnitario'])) for i in items):,.0f} correspondiente a la factura #{invoice_id}.",
                    id_factura=invoice_id,
                    nombre_paciente=paciente.nombre if paciente else None,
                    nombre_profesional=profesional.nombre if profesional else None,
                    monto=sum(Decimal(str(i['precioUnitario'])) for i in items),
                    estado_pago="Pagado",
                    items=[{"descripcion": i["descripcion"], "precio": f"{Decimal(str(i['precioUnitario'])):,.0f}"} for i in items],
                    cta_link=f"{site_url}/aside-patient/facturas.html",
                )
            except Exception as e:
                logger.error(f"Error enviando correo de pago registrado: {e}")

            return {"success": True, "message": "Pago registrado correctamente", "idFactura": invoice_id}, 201
        except Exception as e:
            logger.error("Error registrando pago: %s", e, exc_info=True)
            return {"success": False, "message": "Error al registrar el pago"}, 500

    def get_invoice(self, invoice_id, user_id, user_role):
        factura = self.repo.get_invoice_by_id(invoice_id)
        if not factura:
            return {"success": False, "message": "Factura no encontrada"}, 404

        if user_role not in ("admin",) and factura["idPaciente"] != user_id and factura["idProfesional"] != user_id:
            return {"success": False, "message": "No tienes permiso para ver esta factura"}, 403

        if factura.get("monto"):
            factura["monto"] = float(factura["monto"])
        for item in factura.get("items", []):
            if item.get("precioUnitario"):
                item["precioUnitario"] = float(item["precioUnitario"])

        return {"success": True, "factura": factura}, 200

    def list_patient_invoices(self, patient_id, estado=None, profesional=None, fecha_desde=None, fecha_hasta=None):
        facturas = self.repo.list_invoices_by_patient(
            patient_id, estado=estado, profesional=profesional, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )
        for f in facturas:
            if f.get("monto"):
                f["monto"] = float(f["monto"])
            for item in f.get("items", []):
                if item.get("precioUnitario"):
                    item["precioUnitario"] = float(item["precioUnitario"])
        return {"success": True, "facturas": facturas}, 200

    def list_professional_invoices(self, professional_id, estado=None, paciente=None, fecha_desde=None, fecha_hasta=None):
        facturas = self.repo.list_invoices_by_professional(
            professional_id, estado=estado, paciente=paciente, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )
        for f in facturas:
            if f.get("monto"):
                f["monto"] = float(f["monto"])
        return {"success": True, "facturas": facturas}, 200

    def list_all_invoices(self, paciente=None, profesional=None, estado=None, fecha_desde=None, fecha_hasta=None):
        facturas = self.repo.list_all_invoices(
            paciente=paciente, profesional=profesional, estado=estado,
            fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )
        for f in facturas:
            if f.get("monto"):
                f["monto"] = float(f["monto"])
        return {"success": True, "facturas": facturas}, 200

    def annul_invoice(self, invoice_id, motivo, user_id, user_role):
        if not motivo or not motivo.strip():
            return {"success": False, "message": "Debes indicar el motivo de anulación"}, 400

        row = self.repo.get_invoice_owner(invoice_id)
        if not row:
            return {"success": False, "message": "Factura no encontrada"}, 404

        if row[2]:
            return {"success": False, "message": "La factura ya está anulada"}, 400

        # No se puede anular una factura ya pagada
        factura = self.repo.get_invoice_by_id(invoice_id)
        if factura and factura.get("estadoPago") == "Pagado":
            return {"success": False, "message": "No se puede anular una factura ya pagada"}, 400

        # Solo el profesional dueño puede anular; admin y paciente no
        if user_role != "profesional" or row[1] != user_id:
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
                            estado_pago="Anulada",
                            motivo_anulacion=motivo.strip(),
                            cta_link=f"{site_url}/aside-patient/facturas.html",
                        )
        except Exception as e:
            logger.error(f"Error enviando correo de anulación: {e}")

        return {"success": True, "message": "Factura anulada correctamente"}, 200

    def get_patient_invoice_stats(self, patient_id):
        stats = self.repo.get_invoice_stats_by_patient(patient_id)
        return {"success": True, "stats": stats}, 200

    def get_admin_stats(self):
        stats = self.repo.get_invoice_stats_all()
        return {"success": True, "stats": stats}, 200

    def get_professional_patients(self, professional_id):
        patients = self.repo.get_professional_patients(professional_id)
        return {"success": True, "pacientes": patients}, 200

    def confirm_payment(self, invoice_id, professional_user_id, evidencia,
                        metodoPago=None, referencia=None, notas=None):
        factura_data = self.repo.get_invoice_by_id(invoice_id)
        if not factura_data:
            return {"success": False, "message": "Factura no encontrada"}, 404

        if factura_data.get("anulada"):
            return {"success": False, "message": "No se puede confirmar una factura anulada"}, 400

        if factura_data.get("estadoPago") == "Pagado":
            return {"success": False, "message": "La factura ya está pagada"}, 400

        if factura_data.get("idProfesional") != professional_user_id:
            return {"success": False, "message": "No tienes permiso para confirmar esta factura"}, 403

        if not evidencia:
            return {"success": False, "message": "Debes adjuntar la evidencia del pago"}, 400

        from apps.core.utils import validate_file_upload
        allowed_ext = ["jpg", "jpeg", "png", "webp", "pdf"]
        name, error = validate_file_upload(evidencia, allowed_extensions=allowed_ext)
        if error:
            return {"success": False, "message": f"Evidencia inválida: {error}"}, 400

        if metodoPago:
            allowed_methods = dict(Facturas.METODO_PAGO_CHOICES).keys()
            if metodoPago not in allowed_methods:
                return {"success": False, "message": "Método de pago inválido"}, 400

        from apps.authentication.models import Register
        confirmador = Register.objects.filter(idUsuario=professional_user_id).first()

        ok = self.repo.confirmar_pago(
            invoice_id,
            evidencia=evidencia,
            confirmada_por=confirmador,
            metodoPago=metodoPago,
            referencia=referencia,
            notas=notas,
        )
        if not ok:
            return {"success": False, "message": "No se pudo confirmar el pago"}, 400

        # Enviar correo de notificación al paciente
        try:
            paciente = Register.objects.filter(idUsuario=factura_data["idPaciente"]).first()
            profesional = confirmador
            site_url = InvoiceMailService._get_site_url()
            items_fmt = [
                {"descripcion": i["descripcion"], "precio": f"{float(i['precioUnitario']):,.0f}"}
                for i in factura_data.get("items", [])
            ]
            InvoiceMailService.send_factura_notificacion(
                recipient_email=paciente.email if paciente else None,
                titulo="Pago confirmado",
                mensaje=f"Se ha confirmado el pago de la factura #{invoice_id}.",
                id_factura=invoice_id,
                nombre_paciente=paciente.nombre if paciente else None,
                nombre_profesional=profesional.nombre if profesional else None,
                monto=factura_data.get("monto", 0),
                estado_pago="Pagado",
                items=items_fmt,
                cta_link=f"{site_url}/aside-patient/facturas.html",
            )
        except Exception as e:
            logger.error(f"Error enviando correo de confirmación de pago: {e}")

        return {"success": True, "message": "Pago confirmado y paciente notificado"}, 200