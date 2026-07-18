import hashlib
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.billing.services import InvoiceService
from apps.billing.repositories import InvoiceRepository
from apps.core.permissions import require_auth, require_role

logger = logging.getLogger(__name__)

invoice_service = InvoiceService()
invoice_repo = InvoiceRepository()


class FacturaListView(View):
    def get(self, request):
        user, err = require_auth(request)
        if err:
            return err

        rol = request.GET.get("rol", user["rol"])
        if rol == "paciente":
            payload, status = invoice_service.list_patient_invoices(user["idUsuario"])
        elif rol == "profesional":
            estado = request.GET.get("estado")
            fecha_desde = request.GET.get("fecha_desde")
            fecha_hasta = request.GET.get("fecha_hasta")
            payload, status = invoice_service.list_professional_invoices(
                user["idUsuario"], estado=estado,
                fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
            )
        else:
            payload, status = invoice_service.list_all_invoices(
                paciente=request.GET.get("paciente"),
                profesional=request.GET.get("profesionales"),
                estado=request.GET.get("estado"),
                metodo_pago=request.GET.get("metodoPago"),
                fecha_desde=request.GET.get("fecha_desde"),
                fecha_hasta=request.GET.get("fecha_hasta"),
            )
        return JsonResponse(payload, status=status)

    def post(self, request):
        user, err = require_auth(request)
        if err:
            return err

        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            data = {}

        if user["rol"] == "paciente":
            id_paciente = user["idUsuario"]
            id_profesional = data.get("idProfesional")
            if not id_profesional:
                return JsonResponse({"success": False, "message": "Debes especificar el profesional"}, status=400)
        else:
            id_profesional = data.get("idProfesional") or user["idUsuario"]
            id_paciente = data.get("idPaciente")
            if not id_paciente:
                return JsonResponse({"success": False, "message": "Debes especificar el paciente"}, status=400)

        payload, status = invoice_service.create_invoice(id_paciente, id_profesional, data)
        return JsonResponse(payload, status=status)


class FacturaDetailView(View):
    def get(self, request, id_factura):
        user, err = require_auth(request)
        if err:
            return err
        payload, status = invoice_service.get_invoice(id_factura, user["idUsuario"], user["rol"])
        return JsonResponse(payload, status=status)

    def patch(self, request, id_factura):
        user, err = require_auth(request)
        if err:
            return err

        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            data = {}

        if data.get("anular") or data.get("motivoAnulacion"):
            motivo = data.get("motivoAnulacion", "").strip()
            payload, status = invoice_service.annul_invoice(
                id_factura, motivo, user["idUsuario"], user["rol"],
            )
        else:
            payload, status = invoice_service.update_status(
                id_factura, data.get("estadoPago"), user_id, user_role,
            )
        return JsonResponse(payload, status=status)

    def delete(self, request, id_factura):
        user, err = require_auth(request)
        if err:
            return err

        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            data = {}

        motivo = data.get("motivoAnulacion", "").strip()
        payload, status = invoice_service.annul_invoice(
            id_factura, motivo, user["idUsuario"], user["rol"],
        )
        return JsonResponse(payload, status=status)


class FacturaPagoView(View):
    def post(self, request, id_factura):
        user, err = require_role(request, "paciente")
        if err:
            return err
        payload, status = invoice_service.init_wompi_payment(id_factura, user["idUsuario"])
        return JsonResponse(payload, status=status)

    def delete(self, request, id_factura):
        user, err = require_role(request, "paciente")
        if err:
            return err
        payload, status = invoice_service.cancel_payment(id_factura, user["idUsuario"])
        return JsonResponse(payload, status=status)

    def patch(self, request, id_factura):
        user, err = require_role(request, "paciente")
        if err:
            return err

        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            data = {}

        transaction_id = data.get("transactionId", "")
        if not transaction_id:
            return JsonResponse({"success": False, "message": "Falta el ID de transacción"}, status=400)
        payload, status = invoice_service.confirm_wompi_payment(
            id_factura, transaction_id, user["idUsuario"],
        )
        return JsonResponse(payload, status=status)


class FacturaStatsView(View):
    def get(self, request):
        user, err = require_auth(request)
        if err:
            return err

        rol = request.GET.get("rol", user["rol"])
        if rol == "admin":
            payload, status = invoice_service.get_admin_stats()
        elif rol == "paciente":
            payload, status = invoice_service.get_patient_invoice_stats(user["idUsuario"])
        else:
            payload, status = invoice_service.get_professional_patients(user["idUsuario"])
        return JsonResponse(payload, status=status)


class ProfesionalPacientesView(View):
    def get(self, request):
        user, err = require_role(request, "profesional")
        if err:
            return err
        payload, status = invoice_service.get_professional_patients(user["idUsuario"])
        return JsonResponse(payload, status=status)


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

        if computed != expected_checksum:
            logger.warning("Wompi webhook: firma inválida (ref=%s)", transaction_ref)
            return HttpResponse("", status=200)

        invoice_id = invoice_repo.get_invoice_by_reference(transaction_ref)
        if not invoice_id:
            logger.warning("Wompi webhook: factura no encontrada (ref=%s)", transaction_ref)
            return HttpResponse("", status=200)

        invoice_repo.update_payment_status(invoice_id, "Pagado")
        invoice_repo.set_payment_reference(invoice_id, transaction_ref, transaction_id)
        logger.info(
            "Factura %s pagada vía Wompi (ref=%s, tx=%s)",
            invoice_id, transaction_ref, transaction_id,
        )
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
