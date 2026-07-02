# ARCHIVO: invoice_routes.py
# Facturación y pasarela de pagos Wompi.
# Roles: paciente ve sus facturas; profesional/admin gestionan facturación.
import hashlib
import json

from flask import Blueprint, jsonify, request, session, current_app

from app.services import invoice_service
from app.utils.auth import require_role
from app.repositories import invoice_repository


invoice_bp = Blueprint("invoices", __name__)


@invoice_bp.route("/api/facturas", methods=["POST"])
@require_role("paciente", "profesional", "admin")
def crear_factura():
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


@invoice_bp.route("/api/facturas/mias", methods=["GET"])
@require_role("paciente")
def mis_facturas():
    payload, status = invoice_service.list_patient_invoices(session.get("idUsuario"))
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/emitidas", methods=["GET"])
@require_role("profesional")
def facturas_emitidas():
    estado = request.args.get("estado")
    fecha_desde = request.args.get("fecha_desde")
    fecha_hasta = request.args.get("fecha_hasta")
    payload, status = invoice_service.list_professional_invoices(
        session.get("idUsuario"), estado=estado,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
    )
    return jsonify(payload), status


@invoice_bp.route("/api/facturas", methods=["GET"])
@require_role("admin")
def todas_facturas():
    payload, status = invoice_service.list_all_invoices(
        paciente=request.args.get("paciente"),
        profesional=request.args.get("profesional"),
        estado=request.args.get("estado"),
        metodo_pago=request.args.get("metodoPago"),
        fecha_desde=request.args.get("fecha_desde"),
        fecha_hasta=request.args.get("fecha_hasta"),
    )
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/<int:id_factura>", methods=["GET"])
@require_role("paciente", "profesional", "admin")
def ver_factura(id_factura):
    payload, status = invoice_service.get_invoice(
        id_factura, session.get("idUsuario"), session.get("rol"),
    )
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/<int:id_factura>/estado", methods=["PATCH"])
@require_role("profesional", "admin")
def cambiar_estado_factura(id_factura):
    data = request.get_json() or {}
    payload, status = invoice_service.update_status(
        id_factura, data.get("estadoPago"), session.get("idUsuario"), session.get("rol"),
    )
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/<int:id_factura>/anular", methods=["PATCH"])
@require_role("profesional", "admin")
def anular_factura(id_factura):
    data = request.get_json() or {}
    motivo = data.get("motivoAnulacion", "").strip()
    payload, status = invoice_service.annul_invoice(
        id_factura, motivo, session.get("idUsuario"), session.get("rol"),
    )
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/<int:id_factura>/iniciar-pago", methods=["POST"])
@require_role("paciente")
def iniciar_pago_wompi(id_factura):
    payload, status = invoice_service.init_wompi_payment(id_factura, session.get("idUsuario"))
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/<int:id_factura>/cancelar-pago", methods=["POST"])
@require_role("paciente")
def cancelar_pago_wompi(id_factura):
    payload, status = invoice_service.cancel_payment(id_factura, session.get("idUsuario"))
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/<int:id_factura>/confirmar-pago", methods=["POST"])
@require_role("paciente")
def confirmar_pago_wompi(id_factura):
    data = request.get_json() or {}
    transaction_id = data.get("transactionId", "")
    if not transaction_id:
        return jsonify({"success": False, "message": "Falta el ID de transacción"}), 400
    payload, status = invoice_service.confirm_wompi_payment(id_factura, transaction_id, session.get("idUsuario"))
    return jsonify(payload), status


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

    invoice_id = invoice_repository.get_invoice_by_reference(transaction_ref)
    if not invoice_id:
        current_app.logger.warning("Wompi webhook: factura no encontrada (ref=%s)", transaction_ref)
        return "", 200

    invoice_repository.update_payment_status(invoice_id, "Pagado")
    invoice_repository.set_payment_reference(invoice_id, transaction_ref, transaction_id)
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


@invoice_bp.route("/api/facturas/mis-estadisticas", methods=["GET"])
@require_role("paciente")
def mis_estadisticas_facturas():
    payload, status = invoice_service.get_patient_invoice_stats(session.get("idUsuario"))
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/estadisticas-admin", methods=["GET"])
@require_role("admin")
def estadisticas_admin():
    payload, status = invoice_service.get_admin_stats()
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/pacientes-profesional", methods=["GET"])
@require_role("profesional")
def pacientes_del_profesional():
    payload, status = invoice_service.get_professional_patients(session.get("idUsuario"))
    return jsonify(payload), status



