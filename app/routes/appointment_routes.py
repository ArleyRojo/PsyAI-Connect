# ARCHIVO: appointment_routes.py
# Gestión de citas: crear, listar, cancelar, consultar disponibilidad.
# Roles: paciente crea/cancela/consulta sus citas; profesional gestiona estado y horarios.
from flask import Blueprint, jsonify, request, session

from app.services import appointment_service, invoice_service
from app.utils.auth import require_role


appointment_bp = Blueprint("appointments", __name__)


METODOS_PAGO_SIMULADO = {"pse", "tarjeta"}


def _estado_factura_agendada(metodo_pago):
    return "Pagado" if metodo_pago in METODOS_PAGO_SIMULADO else "Pendiente"


# Helper: extrae paginación de query params
def _get_pagination():
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        limit = 20
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    return page, limit


@appointment_bp.route("/api/citas", methods=["POST"])
@require_role("paciente", "profesional")
def crear_cita():
    data = request.get_json() or {}
    created_by_professional = data.get("creado_por_profesional", False)
    metodo_pago = data.get("metodoPago")

    payload, status = appointment_service.create_appointment(
        session["idUsuario"],
        data,
        created_by_professional=created_by_professional,
    )

    if status == 200 and metodo_pago and session.get("rol") == "paciente":
        id_cita = payload.get("idCita")
        if id_cita:
            professional_id = data.get("idProfesional")
            tipo_cita = data.get("tipoCita", "Consulta")
            desc = f"Consulta psicológica - {tipo_cita}"
            estado_pago = _estado_factura_agendada(metodo_pago)
            invoice_payload, invoice_status = invoice_service.create_invoice(
                professional_id,
                {
                    "idPaciente": session["idUsuario"],
                    "idCita": id_cita,
                    "metodoPago": metodo_pago,
                    "estadoPago": estado_pago,
                    "items": [{"descripcion": desc, "precioUnitario": 100000}],
                },
            )
            if invoice_payload.get("success"):
                payload["idFactura"] = invoice_payload.get("idFactura")
                payload["estadoPagoFactura"] = invoice_payload.get("estadoPago")
            else:
                payload["facturaGenerada"] = False
                payload["facturaError"] = invoice_payload.get("message")
                payload["facturaStatus"] = invoice_status

    return jsonify(payload), status


# Horarios disponibles de un profesional para una fecha (público, sin autenticación)
@appointment_bp.route("/api/citas/disponibles", methods=["GET"])
def horarios_disponibles():
    id_profesional = request.args.get("idProfesional")
    fecha = request.args.get("fecha")
    payload, status = appointment_service.get_available_times(id_profesional, fecha)
    return jsonify(payload), status


@appointment_bp.route("/api/citas/profesional", methods=["GET"])
@require_role("profesional")
def citas_profesional():
    page, limit = _get_pagination()
    payload, status = appointment_service.list_professional_appointments(session.get("idUsuario"), page=page, limit=limit)
    return jsonify(payload), status


@appointment_bp.route("/api/citas/profesional/horarios", methods=["GET"])
@require_role("profesional")
def horarios_ocupados_profesional():
    id_profesional = request.args.get("idProfesional")
    fecha = request.args.get("fecha")
    payload, status = appointment_service.get_taken_slots(id_profesional, fecha)
    return jsonify(payload), status


@appointment_bp.route("/api/citas/proxima", methods=["GET"])
@require_role("paciente")
def proxima_cita_paciente():
    payload, status = appointment_service.get_next_patient_appointment(session.get("idUsuario"))
    return jsonify(payload), status


@appointment_bp.route("/api/citas/solicitadas", methods=["GET"])
@require_role("profesional")
def citas_solicitadas():
    payload, status = appointment_service.list_professional_appointments(session.get("idUsuario"), pending_only=True)
    return jsonify(payload), status


# Cambia estado de una cita (confirmar/rechazar por el profesional)
@appointment_bp.route("/api/citas/<int:id_cita>/estado", methods=["PATCH"])
@require_role("profesional")
def actualizar_estado_cita(id_cita: int):
    data = request.get_json() or {}
    payload, status = appointment_service.update_status(id_cita, data.get("estado"), session.get("idUsuario"))
    return jsonify(payload), status


@appointment_bp.route("/api/citas/paciente", methods=["GET"])
@require_role("paciente")
def citas_paciente():
    payload, status = appointment_service.list_patient_appointments(session.get("idUsuario"))
    return jsonify(payload), status


@appointment_bp.route("/api/citas/<int:id_cita>", methods=["DELETE"])
@require_role("paciente")
def cancelar_cita(id_cita: int):
    data = request.get_json() or {}
    motivo = data.get("motivoCancelacion", "").strip()
    payload, status = appointment_service.cancel_appointment(id_cita, session.get("idUsuario"), motivo)
    return jsonify(payload), status


@appointment_bp.route("/api/citas/profesional/<int:id_cita>/cancelar", methods=["DELETE"])
@require_role("profesional")
def cancelar_cita_profesional(id_cita: int):
    data = request.get_json() or {}
    motivo = data.get("motivoCancelacion", "").strip()
    payload, status = appointment_service.cancel_professional_appointment(
        id_cita, session.get("idUsuario"), motivo
    )
    return jsonify(payload), status


@appointment_bp.route("/api/citas/fechas-disponibles", methods=["GET"])
def fechas_disponibles():
    id_profesional = request.args.get("idProfesional")
    anio = request.args.get("anio")
    mes = request.args.get("mes")
    payload, status = appointment_service.get_available_dates(id_profesional, anio, mes)
    return jsonify(payload), status
