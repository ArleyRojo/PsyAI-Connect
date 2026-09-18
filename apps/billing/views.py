import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status

from apps.billing.services import InvoiceService
from apps.billing.repositories import InvoiceRepository
from apps.core.permissions import IsAuthenticatedDRF, IsPaciente, IsProfesional

logger = logging.getLogger(__name__)

invoice_service = InvoiceService()
invoice_repo = InvoiceRepository()


class FacturaListView(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request):
        user_role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)

        rol = request.query_params.get("rol", user_role)
        if rol == "paciente":
            payload, status_code = invoice_service.list_patient_invoices(user_id)
        elif rol == "profesional":
            estado = request.query_params.get("estado")
            fecha_desde = request.query_params.get("fecha_desde")
            fecha_hasta = request.query_params.get("fecha_hasta")
            payload, status_code = invoice_service.list_professional_invoices(
                user_id,
                estado=estado,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
            )
        else:
            payload, status_code = invoice_service.list_all_invoices(
                paciente=request.query_params.get("paciente"),
                profesional=request.query_params.get("profesionales"),
                estado=request.query_params.get("estado"),
                metodo_pago=request.query_params.get("metodoPago"),
                fecha_desde=request.query_params.get("fecha_desde"),
                fecha_hasta=request.query_params.get("fecha_hasta"),
            )
        return Response(payload, status=status_code)

    def post(self, request):
        user_role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)

        data = request.data if isinstance(request.data, dict) else {}

        if user_role == "paciente":
            id_paciente = user_id
            id_profesional = data.get("idProfesional")
            if not id_profesional:
                return Response(
                    {"success": False, "message": "Debes especificar el profesional"},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )
        else:
            id_profesional = data.get("idProfesional") or user_id
            id_paciente = data.get("idPaciente")
            if not id_paciente:
                return Response(
                    {"success": False, "message": "Debes especificar el paciente"},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )

        payload, status_code = invoice_service.create_invoice(
            id_paciente, id_profesional, data
        )
        return Response(payload, status=status_code)


class FacturaDetailView(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request, id_factura):
        user_id = getattr(request, "user_id", None)
        user_role = getattr(request, "user_role", None)
        payload, status_code = invoice_service.get_invoice(
            id_factura, user_id, user_role
        )
        return Response(payload, status=status_code)

    def patch(self, request, id_factura):
        user_id = getattr(request, "user_id", None)
        user_role = getattr(request, "user_role", None)

        data = request.data if isinstance(request.data, dict) else {}

        if data.get("anular") or data.get("motivoAnulacion"):
            motivo = data.get("motivoAnulacion", "").strip()
            payload, status_code = invoice_service.annul_invoice(
                id_factura, motivo, user_id, user_role
            )
        else:
            payload, status_code = invoice_service.update_status(
                id_factura, data.get("estadoPago"), user_id, user_role
            )
        return Response(payload, status=status_code)

    def delete(self, request, id_factura):
        user_id = getattr(request, "user_id", None)
        user_role = getattr(request, "user_role", None)

        data = request.data if isinstance(request.data, dict) else {}

        motivo = data.get("motivoAnulacion", "").strip()
        payload, status_code = invoice_service.annul_invoice(
            id_factura, motivo, user_id, user_role
        )
        return Response(payload, status=status_code)


class FacturaPagoView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def post(self, request, id_factura):
        user_id = getattr(request, "user_id", None)
        payload, status_code = invoice_service.init_wompi_payment(
            id_factura, user_id
        )
        return Response(payload, status=status_code)

    def delete(self, request, id_factura):
        user_id = getattr(request, "user_id", None)
        payload, status_code = invoice_service.cancel_payment(
            id_factura, user_id
        )
        return Response(payload, status=status_code)

    def patch(self, request, id_factura):
        user_id = getattr(request, "user_id", None)

        data = request.data if isinstance(request.data, dict) else {}

        transaction_id = data.get("transactionId", "")
        if not transaction_id:
            return Response(
                {"success": False, "message": "Falta el ID de transacción"},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        payload, status_code = invoice_service.confirm_wompi_payment(
            id_factura, transaction_id, user_id
        )
        return Response(payload, status=status_code)


class FacturaStatsView(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request):
        user_role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)

        rol = request.query_params.get("rol", user_role)
        if rol == "admin":
            payload, status_code = invoice_service.get_admin_stats()
        elif rol == "paciente":
            payload, status_code = invoice_service.get_patient_invoice_stats(
                user_id
            )
        else:
            payload, status_code = invoice_service.get_professional_patients(
                user_id
            )
        return Response(payload, status=status_code)


class ProfesionalPacientesView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def get(self, request):
        user_id = getattr(request, "user_id", None)
        payload, status_code = invoice_service.get_professional_patients(user_id)
        return Response(payload, status=status_code)


def _send_webhook_payment_emails(invoice_repo, invoice_id):
    try:
        from apps.authentication.models import Register

        factura = invoice_repo.get_invoice_by_id(invoice_id)
        if not factura:
            return
        paciente = Register.objects.filter(
            idUsuario=factura.get("idPaciente")
        ).first()
        profesional = Register.objects.filter(
            idUsuario=factura.get("idProfesional")
        ).first()
        site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
        fecha = ""
        if factura.get("fecha"):
            f = factura["fecha"]
            fecha = (
                f.strftime("%d/%m/%Y %H:%M") if hasattr(f, "strftime") else str(f)
            )
        base_ctx = {
            "id_factura": invoice_id,
            "fecha": fecha,
            "monto": factura.get("monto", 0),
            "metodo_pago": factura.get("metodoPago", "tarjeta"),
            "nombre_paciente": paciente.nombre if paciente else None,
            "nombre_profesional": profesional.nombre if profesional else None,
        }
        if paciente and paciente.email:
            html = render_to_string(
                "emails/pago_confirmado_webhook.html",
                {
                    **base_ctx,
                    "nombre": paciente.nombre,
                    "cta_link": f"{site_url}/aside-patient/facturas.html",
                    "cta_texto": "Ver factura",
                },
            )
            msg = EmailMultiAlternatives(
                "PsyAI Connect — Pago confirmado",
                f"Tu pago de la factura #{invoice_id} ha sido confirmado.",
                to=[paciente.email],
            )
            msg.attach_alternative(html, "text/html")
            msg.send(fail_silently=True)
        if profesional and profesional.email:
            html = render_to_string(
                "emails/pago_confirmado_webhook.html",
                {
                    **base_ctx,
                    "nombre": profesional.nombre,
                    "cta_link": f"{site_url}/aside-professional/facturacion.html",
                    "cta_texto": "Ver factura",
                },
            )
            msg = EmailMultiAlternatives(
                "PsyAI Connect — Pago recibido",
                f"El paciente {paciente.nombre if paciente else ''} ha realizado el pago de la factura #{invoice_id}.",
                to=[profesional.email],
            )
            msg.attach_alternative(html, "text/html")
            msg.send(fail_silently=True)
    except Exception:
        logger.exception(
            "Error enviando correos de pago vía webhook (factura %s)", invoice_id
        )


@method_decorator(csrf_exempt, name="dispatch")
class WebhookWompiView(View):
    def post(self, request):
        events_secret = settings.WOMPI_EVENTS_SECRET
        if not events_secret:
            logger.error("Wompi webhook: WOMPI_EVENTS_SECRET no configurado")
            return HttpResponse("", status=200)

        raw_body = request.body.decode("utf-8", errors="replace")
        try:
            event = json.loads(raw_body)
        except (ValueError, TypeError):
            logger.warning("Wompi webhook: JSON inválido")
            return HttpResponse("", status=200)

        checksum_header = request.headers.get("X-Event-Checksum", "")
        payload_checksum = (event.get("signature") or {}).get("checksum", "")
        expected_checksum = (checksum_header or payload_checksum).upper()
        if not expected_checksum:
            logger.warning("Wompi webhook: sin checksum en request")
            return HttpResponse("", status=200)

        event_name = event.get("event", "")
        if event_name != "transaction.updated":
            return HttpResponse("", status=200)

        data = event.get("data") or {}
        transaction = data.get("transaction") or {}
        transaction_status = transaction.get("status", "")
        transaction_ref = transaction.get("reference", "")
        transaction_id = transaction.get("id", "")

        if transaction_status != "APPROVED" or not transaction_ref:
            return HttpResponse("", status=200)

        props = (event.get("signature") or {}).get("properties", [])
        timestamp = event.get("timestamp", 0)

        raw_values = ""
        for prop in props:
            parts = prop.split(".")
            val = data
            for p in parts:
                val = val.get(p, "") if isinstance(val, dict) else ""
            raw_values += str(val)

        raw_to_sign = f"{raw_values}{timestamp}{events_secret}"
        computed = hashlib.sha256(raw_to_sign.encode()).hexdigest().upper()

        if not hmac.compare_digest(computed, expected_checksum):
            logger.warning(
                "Wompi webhook: firma inválida (ref=%s)", transaction_ref
            )
            return HttpResponse("", status=200)

        invoice_id = invoice_repo.get_invoice_by_reference(transaction_ref)
        if not invoice_id:
            logger.warning(
                "Wompi webhook: factura no encontrada (ref=%s)", transaction_ref
            )
            return HttpResponse("", status=200)

        invoice_repo.update_payment_status(invoice_id, "Pagado")
        invoice_repo.set_payment_reference(invoice_id, transaction_ref, transaction_id)
        logger.info(
            "Factura %s pagada vía Wompi (ref=%s, tx=%s)",
            invoice_id,
            transaction_ref,
            transaction_id,
        )
        _send_webhook_payment_emails(invoice_repo, invoice_id)
        return HttpResponse("", status=200)


def payment_response_view(request):
    transaction_id = request.GET.get("id", "")
    if transaction_id:
        titulo = "Pago procesado"
        mensaje = "Tu transacción ha sido procesada. Puedes cerrar esta ventana."
    else:
        titulo = "Resultado del pago"
        mensaje = "Gracias por tu pago. Puedes cerrar esta ventana."

    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>{titulo}</title>
<style>
body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f5f5f5}}
.card{{background:#fff;border-radius:12px;padding:40px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.1);max-width:400px}}
.icon{{font-size:48px;margin-bottom:16px;color:#43a047}}
h2{{margin:0 0 8px}}p{{color:#666;margin:0 0 24px}}
.btn{{background:#1565C0;color:#fff;border:none;padding:10px 24px;border-radius:6px;cursor:pointer;font-size:14px}}
.btn:hover{{opacity:.9}}
</style></head>
<body>
<div class="card">
<div class="icon">&#10003;</div>
<h2>{titulo}</h2>
<p>{mensaje}</p>
<button class="btn" onclick="window.close()">Cerrar ventana</button>
</div>
</body>
</html>"""
    return HttpResponse(html, content_type="text/html")
