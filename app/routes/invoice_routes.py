# ARCHIVO: invoice_routes.py
# Gestión de facturación: crear, listar, actualizar estado, anular. Nunca eliminar.
# Incluye la integración de pagos con Wompi (checkout redirect + webhook de confirmación).
from flask import Blueprint, jsonify, request, session

from app.services import invoice_service
from app.utils.auth import require_role


invoice_bp = Blueprint("invoices", __name__)


@invoice_bp.route("/api/facturas", methods=["POST"])
@require_role("profesional", "admin")
def crear_factura():
    data = request.get_json() or {}
    professional_id = data.get("idProfesional") if session.get("rol") == "admin" else session.get("idUsuario")
    payload, status = invoice_service.create_invoice(professional_id, data)
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/mias", methods=["GET"])
@require_role("paciente")
def mis_facturas():
    payload, status = invoice_service.list_my_invoices(session.get("idUsuario"))
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/emitidas", methods=["GET"])
@require_role("profesional")
def facturas_emitidas():
    filtros = {
        "paciente": request.args.get("paciente"),
        "estado": request.args.get("estado"),
        "fecha_desde": request.args.get("fecha_desde"),
        "fecha_hasta": request.args.get("fecha_hasta"),
    }
    payload, status = invoice_service.list_issued_invoices(session.get("idUsuario"), filtros)
    return jsonify(payload), status


@invoice_bp.route("/api/facturas", methods=["GET"])
@require_role("admin")
def todas_facturas():
    filtros = {
        "paciente": request.args.get("paciente"),
        "profesional": request.args.get("profesional"),
        "estado": request.args.get("estado"),
        "metodoPago": request.args.get("metodoPago"),
        "fecha_desde": request.args.get("fecha_desde"),
        "fecha_hasta": request.args.get("fecha_hasta"),
    }
    payload, status = invoice_service.list_all_invoices(filtros)
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/<int:id_factura>", methods=["GET"])
@require_role("paciente", "profesional", "admin")
def detalle_factura(id_factura: int):
    payload, status = invoice_service.get_invoice_detail(id_factura, session.get("idUsuario"), session.get("rol"))
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/<int:id_factura>/estado", methods=["PATCH"])
@require_role("profesional", "admin")
def actualizar_estado_factura(id_factura: int):
    data = request.get_json() or {}
    payload, status = invoice_service.update_status(
        id_factura, data.get("estadoPago"), session.get("idUsuario"), session.get("rol")
    )
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/<int:id_factura>/anular", methods=["PATCH"])
@require_role("profesional", "admin")
def anular_factura(id_factura: int):
    data = request.get_json() or {}
    payload, status = invoice_service.annul_invoice(
        id_factura, data.get("motivo", ""), session.get("idUsuario"), session.get("rol")
    )
    return jsonify(payload), status


# ============================================================
# WOMPI — pasarela de pagos (PSE / tarjeta)
# ============================================================

@invoice_bp.route("/api/facturas/<int:id_factura>/iniciar-pago", methods=["POST"])
@require_role("paciente")
def iniciar_pago_factura(id_factura: int):
    redirect_url = f"{request.url_root.rstrip('/')}/aside-patient/facturas.html?factura={id_factura}"
    payload, status = invoice_service.iniciar_pago_wompi(id_factura, session.get("idUsuario"), redirect_url)
    return jsonify(payload), status


@invoice_bp.route("/api/facturas/<int:id_factura>/verificar-pago", methods=["GET"])
@require_role("paciente")
def verificar_pago_factura(id_factura: int):
    transaction_id = request.args.get("transactionId")
    payload, status = invoice_service.verificar_pago_wompi(id_factura, transaction_id, session.get("idUsuario"))
    return jsonify(payload), status


# Webhook público de Wompi: sin sesión ni CSRF, autenticado por firma HMAC-SHA256
# (ver app/__init__.py donde se exime de CSRF y invoice_service.procesar_evento_wompi).
@invoice_bp.route("/api/webhooks/wompi", methods=["POST"])
def webhook_wompi():
    payload = request.get_json(silent=True) or {}
    resultado, status = invoice_service.procesar_evento_wompi(payload)
    return jsonify(resultado), status
