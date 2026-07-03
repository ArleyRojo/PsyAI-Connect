import hashlib
import json

from flask import Blueprint, jsonify, request, session, current_app
from flask.views import MethodView

from app.services.invoice_service import InvoiceService
from app.repositories.invoice_repository import InvoiceRepository
from app.utils.route_helpers import RouteHelpers


invoice_bp = Blueprint("invoices", __name__)
invoice_service = InvoiceService()


class FacturaResource(MethodView):
    def get(self, id_factura=None):
        if id_factura:
            err = RouteHelpers.check_role("paciente", "profesional", "admin")
            if err:
                return err
            payload, status = invoice_service.get_invoice(
                id_factura, session.get("idUsuario"), session.get("rol"),
            )
            return jsonify(payload), status

        rol = request.args.get("rol", session.get("rol"))
        err = RouteHelpers.check_role("paciente", "profesional", "admin")
        if err:
            return err

        if rol == "paciente":
            payload, status = invoice_service.list_patient_invoices(session.get("idUsuario"))
        elif rol == "profesional":
            estado = request.args.get("estado")
            fecha_desde = request.args.get("fecha_desde")
            fecha_hasta = request.args.get("fecha_hasta")
            payload, status = invoice_service.list_professional_invoices(
                session.get("idUsuario"), estado=estado,
                fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
            )
        else:
            payload, status = invoice_service.list_all_invoices(
                paciente=request.args.get("paciente"),
                profesional=request.args.get("profesional"),
                estado=request.args.get("estado"),
                metodo_pago=request.args.get("metodoPago"),
                fecha_desde=request.args.get("fecha_desde"),
                fecha_hasta=request.args.get("fecha_hasta"),
            )
        return jsonify(payload), status

    def post(self):
        err = RouteHelpers.check_role("paciente", "profesional", "admin")
        if err:
            return err
        data = request.get_json() or {}
        user_role = session.get("rol")
        user_id = session.get("idUsuario")

        if user_role == "paciente":
            id_paciente = user_id
            id_profesional = data.get("idProfesional")
            if not id_profesional:
                return jsonify({"success": False, "message": "Debes especificar el profesional"}), 400
        else:
            id_profesional = data.get("idProfesional") or user_id
            id_paciente = data.get("idPaciente")
            if not id_paciente:
                return jsonify({"success": False, "message": "Debes especificar el paciente"}), 400

        payload, status = invoice_service.create_invoice(id_paciente, id_profesional, data)
        return jsonify(payload), status

    def patch(self, id_factura):
        data = request.get_json() or {}
        if data.get("anular") or data.get("motivoAnulacion"):
            err = RouteHelpers.check_role("profesional", "admin")
            if err:
                return err
            motivo = data.get("motivoAnulacion", "").strip()
            payload, status = invoice_service.annul_invoice(
                id_factura, motivo, session.get("idUsuario"), session.get("rol"),
            )
        else:
            err = RouteHelpers.check_role("profesional", "admin")
            if err:
                return err
            payload, status = invoice_service.update_status(
                id_factura, data.get("estadoPago"), session.get("idUsuario"), session.get("rol"),
            )
        return jsonify(payload), status

    def delete(self, id_factura):
        data = request.get_json() or {}
        err = RouteHelpers.check_role("profesional", "admin")
        if err:
            return err
        motivo = data.get("motivoAnulacion", "").strip()
        payload, status = invoice_service.annul_invoice(
            id_factura, motivo, session.get("idUsuario"), session.get("rol"),
        )
        return jsonify(payload), status


class FacturaPagoResource(MethodView):
    def post(self, id_factura):
        err = RouteHelpers.check_role("paciente")
        if err:
            return err
        payload, status = invoice_service.init_wompi_payment(id_factura, session.get("idUsuario"))
        return jsonify(payload), status

    def delete(self, id_factura):
        err = RouteHelpers.check_role("paciente")
        if err:
            return err
        payload, status = invoice_service.cancel_payment(id_factura, session.get("idUsuario"))
        return jsonify(payload), status

    def patch(self, id_factura):
        err = RouteHelpers.check_role("paciente")
        if err:
            return err
        data = request.get_json() or {}
        transaction_id = data.get("transactionId", "")
        if not transaction_id:
            return jsonify({"success": False, "message": "Falta el ID de transacción"}), 400
        payload, status = invoice_service.confirm_wompi_payment(
            id_factura, transaction_id, session.get("idUsuario"),
        )
        return jsonify(payload), status


class FacturaStatsResource(MethodView):
    def get(self):
        rol = request.args.get("rol", session.get("rol"))
        if rol == "admin":
            err = RouteHelpers.check_role("admin")
            if err:
                return err
            payload, status = invoice_service.get_admin_stats()
        elif rol == "paciente":
            err = RouteHelpers.check_role("paciente")
            if err:
                return err
            payload, status = invoice_service.get_patient_invoice_stats(session.get("idUsuario"))
        else:
            err = RouteHelpers.check_role("profesional")
            if err:
                return err
            payload, status = invoice_service.get_professional_patients(session.get("idUsuario"))
        return jsonify(payload), status


class ProfesionalPacientesResource(MethodView):
    def get(self):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        payload, status = invoice_service.get_professional_patients(session.get("idUsuario"))
        return jsonify(payload), status


invoice_bp.add_url_rule("/api/facturas", view_func=FacturaResource.as_view("facturas"))
invoice_bp.add_url_rule("/api/facturas/mias", view_func=FacturaResource.as_view("facturas_mias"))
invoice_bp.add_url_rule("/api/facturas/<int:id_factura>", view_func=FacturaResource.as_view("factura"))
invoice_bp.add_url_rule("/api/facturas/<int:id_factura>/pago", view_func=FacturaPagoResource.as_view("factura_pago"))
invoice_bp.add_url_rule("/api/facturas/<int:id_factura>/iniciar-pago", view_func=FacturaPagoResource.as_view("factura_iniciar_pago"))
@invoice_bp.route("/api/facturas/<int:id_factura>/confirmar-pago", methods=["POST"])
def confirmar_pago_wompi(id_factura):
    err = RouteHelpers.check_role("paciente")
    if err:
        return err
    data = request.get_json() or {}
    transaction_id = data.get("transactionId", "")
    if not transaction_id:
        return jsonify({"success": False, "message": "Falta el ID de transacción"}), 400
    payload, status = invoice_service.confirm_wompi_payment(
        id_factura, transaction_id, session.get("idUsuario"),
    )
    return jsonify(payload), status
invoice_bp.add_url_rule("/api/facturas/stats", view_func=FacturaStatsResource.as_view("factura_stats"))
invoice_bp.add_url_rule("/api/facturas/estadisticas-admin", view_func=FacturaStatsResource.as_view("factura_estadisticas_admin"))
invoice_bp.add_url_rule("/api/facturas/emitidas", view_func=FacturaResource.as_view("facturas_emitidas"))
invoice_bp.add_url_rule("/api/facturas/pacientes-profesional", view_func=ProfesionalPacientesResource.as_view("factura_pacientes"))


@invoice_bp.route("/api/webhooks/wompi", methods=["POST"])
def webhook_wompi():
    events_secret = current_app.config.get("WOMPI_EVENTS_SECRET")
    if not events_secret:
        current_app.logger.error("Wompi webhook: WOMPI_EVENTS_SECRET no configurado")
        return "", 200

    raw_body = request.get_data(as_text=True)
    try:
        event = json.loads(raw_body)
    except (ValueError, TypeError):
        current_app.logger.warning("Wompi webhook: JSON inválido")
        return "", 200

    checksum_header = request.headers.get("X-Event-Checksum", "")
    payload_checksum = (event.get("signature") or {}).get("checksum", "")
    expected_checksum = (checksum_header or payload_checksum).upper()
    if not expected_checksum:
        current_app.logger.warning("Wompi webhook: sin checksum en request")
        return "", 200

    event_name = event.get("event", "")
    if event_name != "transaction.updated":
        return "", 200

    data = event.get("data") or {}
    transaction = data.get("transaction") or {}
    transaction_status = transaction.get("status", "")
    transaction_ref = transaction.get("reference", "")
    transaction_id = transaction.get("id", "")

    if transaction_status != "APPROVED" or not transaction_ref:
        return "", 200

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
        current_app.logger.warning("Wompi webhook: firma inválida (ref=%s)", transaction_ref)
        return "", 200

    invoice_id = InvoiceRepository().get_invoice_by_reference(transaction_ref)
    if not invoice_id:
        current_app.logger.warning("Wompi webhook: factura no encontrada (ref=%s)", transaction_ref)
        return "", 200

    InvoiceRepository().update_payment_status(invoice_id, "Pagado")
    InvoiceRepository().set_payment_reference(invoice_id, transaction_ref, transaction_id)
    current_app.logger.info(
        "Factura %s pagada vía Wompi (ref=%s, tx=%s)",
        invoice_id, transaction_ref, transaction_id,
    )
    return "", 200


@invoice_bp.route("/api/pagos/respuesta", methods=["GET"])
def respuesta_pago_wompi():
    transaction_id = request.args.get("id", "")
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
    return html
