# ARCHIVO: professional_routes.py
# Rutas del profesional: perfil, disponibilidad, dashboard, pacientes, diagnósticos, reportes,
# evolución de pacientes, historial chatbot, documentos, descarga de archivos y mensajería directa.
import os

from flask import Blueprint, current_app, jsonify, request, session

from app.services import mensajes_service, professional_service
from app.utils.auth import require_role, require_authenticated


professional_bp = Blueprint("professional", __name__)


@professional_bp.route("/api/perfil/profesional/<int:id_usuario>", methods=["GET"])
@require_role("admin", "profesional", "paciente")
def get_perfil_profesional(id_usuario: int):
    payload, status = professional_service.get_profile(id_usuario)
    return jsonify(payload), status


# Edita perfil propio; evita que edite el perfil de otro profesional
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


# Gestión de disponibilidad horaria para citas
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


# Dashboard, listado de pacientes asignados
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


# Diagnósticos: guardar y ver historial
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


# Reportes clínicos: CRUD completo + listado de eliminados
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


# Evolución de todos los pacientes del profesional
@professional_bp.route("/api/evolucion/profesional", methods=["GET"])
@require_role("profesional")
def evolucion_todos_pacientes():
    payload, status = professional_service.all_evolution(session.get("idUsuario"))
    return jsonify(payload), status


# Historial de chatbot de un paciente específico (vista profesional/admin)
@professional_bp.route("/api/profesional/paciente/<int:id_paciente>/chatbot-historial", methods=["GET"])
@require_role("profesional", "admin")
def paciente_chatbot_historial(id_paciente: int):
    auth_error = require_authenticated()
    if auth_error:
        return auth_error
    payload, status = professional_service.get_patient_chatbot_history(session.get("idUsuario"), id_paciente)
    return jsonify(payload), status


# -- HISTORIA CLINICA / DOCUMENTOS -------------------------------------
@professional_bp.route("/api/profesional/paciente/<int:id_paciente>/documentos", methods=["GET"])
@require_role("profesional")
def listar_documentos_paciente(id_paciente: int):
    from app.services import documento_service
    payload = documento_service.list_patient_docs(session.get("idUsuario"), id_paciente)
    return jsonify(payload), (200 if payload.get("success") else 500)


@professional_bp.route("/api/profesional/paciente/<int:id_paciente>/documentos", methods=["POST"])
@require_role("profesional")
def subir_documento_paciente(id_paciente: int):
    from app.services import documento_service
    file = request.files.get("archivo")
    categoria = request.form.get("categoria", "Otro")
    visibilidad = request.form.get("visibilidad", "privado")
    notas = request.form.get("notas", "")
    payload, status = documento_service.upload_profesional_doc(
        session.get("idUsuario"), id_paciente, file, categoria, visibilidad, notas,
    )
    return jsonify(payload), status


@professional_bp.route("/api/profesional/documentos/<int:id_documento>/visibilidad", methods=["PUT"])
@require_role("profesional")
def toggle_visibilidad_documento(id_documento: int):
    from app.services import documento_service
    payload, status = documento_service.toggle_doc_visibility(id_documento, session.get("idUsuario"))
    return jsonify(payload), status


@professional_bp.route("/api/profesional/documentos/<int:id_documento>", methods=["DELETE"])
@require_role("profesional")
def eliminar_documento_profesional(id_documento: int):
    from app.services import documento_service
    payload, status = documento_service.delete_profesional_doc(id_documento, session.get("idUsuario"))
    return jsonify(payload), status


# -- SERVIDOR DE ARCHIVOS -----------------------------------------------
# Descarga física de documentos desde el sistema de archivos
@professional_bp.route("/api/descargar/documento-profesional/<int:id_documento>", methods=["GET"])
@require_role("profesional")
def descargar_documento_profesional(id_documento: int):
    from flask import send_file
    from app.services import documento_service
    doc, err, status = documento_service.get_profesional_doc_for_download(id_documento, session.get("idUsuario"))
    if err:
        return jsonify(err), status
    path = os.path.join(current_app.root_path, "static", doc["rutaArchivo"])
    if not os.path.exists(path):
        return jsonify({"success": False, "message": "Archivo no encontrado en el servidor"}), 404
    return send_file(path, download_name=doc["nombreArchivo"], as_attachment=False)


@professional_bp.route("/api/descargar/documento-paciente/<int:id_documento>", methods=["GET"])
@require_role("profesional", "paciente")
def descargar_documento_paciente(id_documento: int):
    from flask import send_file
    from app.services import documento_service
    doc, err, status = documento_service.get_patient_doc_for_download(
        id_documento, session.get("idUsuario"), session.get("rol")
    )
    if err:
        return jsonify(err), status
    path = os.path.join(current_app.root_path, "static", doc["rutaArchivo"])
    if not os.path.exists(path):
        return jsonify({"success": False, "message": "Archivo no encontrado en el servidor"}), 404
    return send_file(path, download_name=doc["nombreArchivo"], as_attachment=False)


# -- MENSAJERIA DIRECTA -------------------------------------------------
# Lista pacientes para chat, enriqueciendo con último mensaje y no leídos
@professional_bp.route("/api/chat/pacientes", methods=["GET"])
@require_role("profesional")
def chat_listar_pacientes():
    """
    Devuelve los pacientes registrados con ultimo mensaje y no-leidos.
    """
    id_profesional = session.get("idUsuario")
    pacientes = professional_service.list_patients_for_chat()
    resultado = mensajes_service.get_contactos_con_mensajes(id_profesional, pacientes)
    return jsonify({"success": True, "pacientes": resultado}), 200


@professional_bp.route("/api/profesional/chat/mensajes", methods=["GET"])
@require_role("paciente", "profesional")
def chat_get_mensajes_profesional():
    id_paciente = request.args.get("receptor", type=int)
    if not id_paciente:
        return jsonify({"success": False, "message": "Falta receptor"}), 400
    msgs = mensajes_service.get_mensajes(session.get("idUsuario"), id_paciente, request.args.get("desde", default=0, type=int))
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

    id_msg = mensajes_service.enviar_mensaje(session.get("idUsuario"), receptor, mensaje)
    return jsonify({"success": True, "idMensaje": id_msg}), 201
