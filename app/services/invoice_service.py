# ============================================================
# ARCHIVO: services/invoice_service.py
# ============================================================

import hashlib
import hmac
import secrets

import requests
from mysql.connector.errors import DatabaseError

from app.config import Config
from app.repositories import invoice_repository

ESTADOS_VALIDOS = {"Pendiente", "Parcial", "Pagado"}
METODOS_VALIDOS = {"banco", "tarjeta", "efectivo", "transferencia"}

ERRNO_SIGNAL = 1644  # SIGNAL SQLSTATE '45000' del trigger trg_evitar_factura_duplicada

WOMPI_CURRENCY = "COP"


def create_invoice(professional_id, data):
    patient_id = data.get("idPaciente")
    cita_id = data.get("idCita")
    items = data.get("items") or []
    metodo_pago = data.get("metodoPago")

    if not professional_id or not patient_id or not metodo_pago or not items:
        return {"success": False, "message": "Datos incompletos"}, 400
    if metodo_pago not in METODOS_VALIDOS:
        return {"success": False, "message": "Método de pago inválido"}, 400

    for item in items:
        precio = item.get("precioUnitario")
        if not item.get("descripcion") or precio in (None, ""):
            return {"success": False, "message": "Cada ítem requiere descripción y precio"}, 400
        try:
            if float(precio) <= 0:
                return {"success": False, "message": "El precio de cada ítem debe ser mayor a cero"}, 400
        except (TypeError, ValueError):
            return {"success": False, "message": "Precio de ítem inválido"}, 400

    try:
        invoice_id = invoice_repository.create_invoice(patient_id, professional_id, cita_id, items, metodo_pago)
    except DatabaseError as e:
        if e.errno == ERRNO_SIGNAL:
            return {"success": False, "message": e.msg or "Ya existe una factura para este paciente hoy"}, 409
        raise

    return {"success": True, "message": "Factura creada correctamente", "idFactura": invoice_id}, 200


def get_invoice_detail(invoice_id, requester_id, requester_role):
    owner = invoice_repository.get_invoice_owner(invoice_id)
    if not owner:
        return {"success": False, "message": "Factura no encontrada"}, 404

    id_paciente, id_profesional, _anulada = owner
    if requester_role == "paciente" and id_paciente != requester_id:
        return {"success": False, "message": "No tienes permiso"}, 403
    if requester_role == "profesional" and id_profesional != requester_id:
        return {"success": False, "message": "No tienes permiso"}, 403

    return {"success": True, "factura": invoice_repository.get_invoice_by_id(invoice_id)}, 200


def list_my_invoices(patient_id):
    return {"success": True, "facturas": invoice_repository.list_invoices_by_patient(patient_id)}, 200


def list_issued_invoices(professional_id, filtros):
    return {"success": True, "facturas": invoice_repository.list_invoices_by_professional(professional_id, filtros)}, 200


def list_all_invoices(filtros):
    return {"success": True, "facturas": invoice_repository.list_all_invoices(filtros)}, 200


def update_status(invoice_id, nuevo_estado, requester_id, requester_role):
    # El paciente nunca puede auto-marcarse como pagado: los pagos en línea (PSE/tarjeta)
    # se confirman solo vía webhook de Wompi, y efectivo/transferencia los confirma
    # manualmente el profesional o un admin tras verificar el ingreso.
    if requester_role == "paciente":
        return {"success": False, "message": "Solo el profesional o un administrador pueden actualizar el estado de pago"}, 403

    if nuevo_estado not in ESTADOS_VALIDOS:
        return {"success": False, "message": "Estado inválido"}, 400

    owner = invoice_repository.get_invoice_owner(invoice_id)
    if not owner:
        return {"success": False, "message": "Factura no encontrada"}, 404

    id_paciente, id_profesional, anulada = owner
    if anulada:
        return {"success": False, "message": "No se puede modificar una factura anulada"}, 400

    if requester_role == "profesional" and id_profesional != requester_id:
        return {"success": False, "message": "No tienes permiso"}, 403

    rowcount = invoice_repository.update_payment_status(invoice_id, nuevo_estado)
    if rowcount == 0:
        return {"success": False, "message": "No se pudo actualizar la factura"}, 400
    return {"success": True, "message": "Estado de la factura actualizado"}, 200


def annul_invoice(invoice_id, motivo, requester_id, requester_role):
    if not motivo or not motivo.strip():
        return {"success": False, "message": "Debes indicar el motivo de la anulación"}, 400

    owner = invoice_repository.get_invoice_owner(invoice_id)
    if not owner:
        return {"success": False, "message": "Factura no encontrada"}, 404

    _id_paciente, id_profesional, anulada = owner
    if anulada:
        return {"success": False, "message": "La factura ya se encuentra anulada"}, 400
    if requester_role == "profesional" and id_profesional != requester_id:
        return {"success": False, "message": "No tienes permiso"}, 403

    rowcount = invoice_repository.annul_invoice(invoice_id, motivo.strip())
    if rowcount == 0:
        return {"success": False, "message": "No se pudo anular la factura"}, 400
    return {"success": True, "message": "Factura anulada correctamente"}, 200


# ============================================================
# WOMPI — pasarela de pagos (PSE / tarjeta)
# https://docs.wompi.co
# ============================================================

def _wompi_configured():
    return bool(Config.WOMPI_PUBLIC_KEY and Config.WOMPI_INTEGRITY_SECRET)


def _resolve_path(data, dotted_path):
    node = data
    for part in dotted_path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def iniciar_pago_wompi(invoice_id, patient_id, redirect_url):
    info = invoice_repository.get_invoice_payment_info(invoice_id)
    if not info:
        return {"success": False, "message": "Factura no encontrada"}, 404
    if info["idPaciente"] != patient_id:
        return {"success": False, "message": "No tienes permiso"}, 403
    if info["anulada"]:
        return {"success": False, "message": "La factura está anulada"}, 400
    if info["estadoPago"] == "Pagado":
        return {"success": False, "message": "La factura ya está pagada"}, 400
    if not _wompi_configured():
        return {"success": False, "message": "La pasarela de pagos no está configurada todavía"}, 503

    amount_in_cents = int(round(float(info["monto"]) * 100))
    # Referencia única por intento: si el paciente cancela y reintenta, no choca con la anterior
    reference = f"PSY{invoice_id}-{secrets.token_hex(6)}"
    signature = hashlib.sha256(
        f"{reference}{amount_in_cents}{WOMPI_CURRENCY}{Config.WOMPI_INTEGRITY_SECRET}".encode("utf-8")
    ).hexdigest()

    invoice_repository.set_wompi_reference(invoice_id, reference)

    return {
        "success": True,
        "checkoutUrl": Config.WOMPI_CHECKOUT_URL,
        "publicKey": Config.WOMPI_PUBLIC_KEY,
        "currency": WOMPI_CURRENCY,
        "amountInCents": amount_in_cents,
        "reference": reference,
        "signature": signature,
        "redirectUrl": redirect_url,
    }, 200


def verificar_pago_wompi(invoice_id, transaction_id, requester_id):
    """Reconciliación al volver del checkout: consulta el estado real en Wompi
    en caso de que el webhook aún no haya llegado."""
    info = invoice_repository.get_invoice_payment_info(invoice_id)
    if not info:
        return {"success": False, "message": "Factura no encontrada"}, 404
    if info["idPaciente"] != requester_id:
        return {"success": False, "message": "No tienes permiso"}, 403
    if not transaction_id:
        return {"success": False, "message": "Falta el identificador de la transacción"}, 400
    if not _wompi_configured():
        return {"success": False, "message": "La pasarela de pagos no está configurada todavía"}, 503

    try:
        resp = requests.get(
            f"{Config.WOMPI_API_BASE}/transactions/{transaction_id}",
            headers={"Authorization": f"Bearer {Config.WOMPI_PUBLIC_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        transaction = (resp.json() or {}).get("data") or {}
    except requests.RequestException:
        return {"success": False, "message": "No se pudo verificar el pago con Wompi"}, 502

    if transaction.get("reference") != info["wompiReference"]:
        return {"success": False, "message": "La transacción no corresponde a esta factura"}, 400

    status = transaction.get("status")
    if status == "APPROVED":
        invoice_repository.mark_paid_by_wompi(invoice_id, transaction.get("id"))
        return {"success": True, "estadoPago": "Pagado", "wompiStatus": status}, 200

    return {"success": True, "estadoPago": info["estadoPago"], "wompiStatus": status}, 200


def procesar_evento_wompi(payload):
    """Webhook de Wompi: valida el checksum y marca la factura como pagada.
    Siempre responde 200 salvo firma inválida, para no generar reintentos infinitos
    por facturas/eventos que ya no aplican."""
    if not Config.WOMPI_EVENTS_SECRET:
        return {"success": False, "message": "Webhook no configurado"}, 503

    signature_block = payload.get("signature") or {}
    properties = signature_block.get("properties") or []
    checksum_received = str(signature_block.get("checksum") or "")
    timestamp = payload.get("timestamp")
    data = payload.get("data") or {}

    if not properties or not checksum_received or timestamp is None:
        return {"success": False, "message": "Payload inválido"}, 400

    concatenated = "".join(str(_resolve_path(data, prop)) for prop in properties)
    concatenated += f"{timestamp}{Config.WOMPI_EVENTS_SECRET}"
    checksum_calculado = hashlib.sha256(concatenated.encode("utf-8")).hexdigest()

    if not hmac.compare_digest(checksum_calculado.lower(), checksum_received.lower()):
        return {"success": False, "message": "Firma inválida"}, 401

    transaction = data.get("transaction") or {}
    reference = transaction.get("reference")
    status = transaction.get("status")
    transaction_id = transaction.get("id")

    if not reference:
        return {"success": True, "message": "Evento sin referencia, ignorado"}, 200

    invoice = invoice_repository.get_invoice_by_wompi_reference(reference)
    if not invoice:
        return {"success": True, "message": "Factura no encontrada para esta referencia"}, 200

    if status == "APPROVED":
        invoice_repository.mark_paid_by_wompi(invoice["idFactura"], transaction_id)

    return {"success": True}, 200
