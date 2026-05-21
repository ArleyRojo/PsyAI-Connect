from flask import Blueprint, jsonify, request, session

from app.repositories import mensajes_repository
from app.services import professional_service
from app.utils.auth import require_role, require_authenticated


professional_bp = Blueprint("professional", __name__)


def _ordenar_contactos_chat(contactos):
    return sorted(
        contactos,
        key=lambda contacto: (
            1 if contacto.get("noLeidos", 0) else 0,
            contacto.get("ultimaFecha") or "",
            contacto.get("ultimoIdMensaje") or 0,
        ),
        reverse=True,
    )


@professional_bp.route("/api/perfil/profesional/<int:id_usuario>", methods=["GET"])
@require_role("admin", "profesional", "paciente")
def get_perfil_profesional(id_usuario: int):
    payload, status = professional_service.get_profile(id_usuario)
    return jsonify(payload), status


@professional_bp.route("/api/perfil/profesional", methods=["PUT"])
@require_role("profesional")
def editar_perfil_profesional():
    data = request.get_json() or {}
    user_id = session.get("idUsuario")

    if data.get("idUsuario") and data["idUsuario"] != user_id:
        return jsonify({"success": False, "message": "No tienes permiso para editar este perfil"}), 403

    data["idUsuario"] = user_id
    payload, status = professional_service.update_profile(data)
    return jsonify(payload), status


@professional_bp.route("/api/disponibilidad", methods=["POST"])
@require_role("profesional")
def crear_disponibilidad():
    payload, status = professional_service.create_availability(session.get("idUsuario"), request.get_json() or {})
    return jsonify(payload), status


@professional_bp.route("/api/disponibilidad/<int:id_profesional>", methods=["GET"])
@require_role("admin", "profesional", "paciente")
def ver_disponibilidad(id_profesional: int):
    payload, status = professional_service.get_availability(id_profesional)
    return jsonify(payload), status


@professional_bp.route("/api/profesional/dashboard", methods=["GET"])
@require_role("profesional")
def dashboard_profesional():
    payload, status = professional_service.get_dashboard(session.get("idUsuario"))
    return jsonify(payload), status


@professional_bp.route("/api/profesional/pacientes", methods=["GET"])
@require_role("profesional")
def listar_pacientes_profesional():
    payload, status = professional_service.list_patients(session.get("idUsuario"))
    return jsonify(payload), status


@professional_bp.route("/api/diagnosticos", methods=["POST"])
@require_role("profesional")
def guardar_diagnostico():
    payload, status = professional_service.save_diagnosis(session.get("idUsuario"), request.get_json() or {})
    return jsonify(payload), status


@professional_bp.route("/api/diagnosticos", methods=["GET"])
@require_role("profesional")
def historial_diagnosticos():
    payload, status = professional_service.diagnosis_history(session.get("idUsuario"))
    return jsonify(payload), status


@professional_bp.route("/api/reportes/profesional", methods=["GET"])
@require_role("profesional")
def listar_reportes_profesional():
    payload, status = professional_service.report_overview(session.get("idUsuario"))
    return jsonify(payload), status


@professional_bp.route("/api/reportes/eliminados", methods=["GET"])
@require_role("profesional")
def reportes_eliminados():
    payload, status = professional_service.get_deleted_reports(session.get("idUsuario"))
    return jsonify(payload), status


@professional_bp.route("/api/reportes", methods=["POST"])
@require_role("profesional")
def crear_reporte():
    payload, status = professional_service.create_report(session.get("idUsuario"), request.get_json() or {})
    return jsonify(payload), status


@professional_bp.route("/api/reportes/<int:id_reporte>", methods=["PUT"])
@require_role("profesional")
def editar_reporte(id_reporte: int):
    data = request.get_json() or {}
    data["idReporte"] = id_reporte
    payload, status = professional_service.update_report(session.get("idUsuario"), data)
    return jsonify(payload), status


@professional_bp.route("/api/reportes/<int:id_reporte>", methods=["DELETE"])
@require_role("profesional")
def eliminar_reporte(id_reporte: int):
    payload, status = professional_service.delete_report(session.get("idUsuario"), id_reporte)
    return jsonify(payload), status


@professional_bp.route("/api/evolucion/profesional", methods=["GET"])
@require_role("profesional")
def evolucion_todos_pacientes():
    payload, status = professional_service.all_evolution(session.get("idUsuario"))
    return jsonify(payload), status


@professional_bp.route("/api/profesional/paciente/<int:id_paciente>/chatbot-historial", methods=["GET"])
@require_role("profesional", "admin")
def paciente_chatbot_historial(id_paciente: int):
    auth_error = require_authenticated()
    if auth_error:
        return auth_error
    payload, status = professional_service.get_patient_chatbot_history(session.get("idUsuario"), id_paciente)
    return jsonify(payload), status


# -- MENSAJERIA DIRECTA -------------------------------------------------
@professional_bp.route("/api/chat/pacientes", methods=["GET"])
@require_role("profesional")
def chat_listar_pacientes():
    """
    Devuelve los pacientes registrados con ultimo mensaje y no-leidos.
    """
    from app.repositories import professional_repository

    id_profesional = session.get("idUsuario")
    pacientes = professional_repository.list_patients_for_chat()
    resultado = []

    for paciente in pacientes:
        ultimo = mensajes_repository.get_ultimo_mensaje(id_profesional, paciente["idUsuario"])
        no_leidos = mensajes_repository.contar_no_leidos(id_profesional, paciente["idUsuario"])
        resultado.append({
            **paciente,
            "ultimoMensaje": ultimo["mensaje"][:60] if ultimo else None,
            "ultimaFecha": str(ultimo["fecha"]) if ultimo else None,
            "ultimoIdMensaje": ultimo["idMensaje"] if ultimo else 0,
            "ultimoEmisor": ultimo["idEmisor"] if ultimo else None,
            "noLeidos": no_leidos,
        })

    resultado = _ordenar_contactos_chat(resultado)
    return jsonify({"success": True, "pacientes": resultado}), 200


@professional_bp.route("/api/profesional/chat/mensajes", methods=["GET"])
@require_role("paciente", "profesional")
def chat_get_mensajes_profesional():
    id_profesional = session.get("idUsuario")
    id_paciente = request.args.get("receptor", type=int)
    desde_id = request.args.get("desde", default=0, type=int)

    if not id_paciente:
        return jsonify({"success": False, "message": "Falta receptor"}), 400

    mensajes_repository.marcar_leidos(id_profesional, id_paciente)
    rows = mensajes_repository.get_conversacion(id_profesional, id_paciente, desde_id)
    msgs = [
        {**row, "esMio": row["idEmisor"] == id_profesional, "fecha": str(row["fecha"])}
        for row in rows
    ]
    return jsonify({"success": True, "mensajes": msgs}), 200


@professional_bp.route("/api/profesional/chat/enviar", methods=["POST"])
@require_role("paciente", "profesional")
def chat_enviar_profesional():
    data = request.get_json() or {}
    receptor = data.get("receptor")
    mensaje = (data.get("mensaje") or "").strip()

    if not receptor or not mensaje:
        return jsonify({"success": False, "message": "Datos incompletos"}), 400
    if len(mensaje) > 2000:
        return jsonify({"success": False, "message": "Mensaje demasiado largo"}), 400

    id_msg = mensajes_repository.enviar_mensaje(session.get("idUsuario"), receptor, mensaje)
    return jsonify({"success": True, "idMensaje": id_msg}), 201
