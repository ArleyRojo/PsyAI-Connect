from queue import Empty

from flask import Blueprint, Response, jsonify, request, session, stream_with_context

from app.services import chatbot_config_events, chatbot_config_service, chatbot_service, patient_service
from app.utils.auth import require_role, require_authenticated


patient_bp = Blueprint("patient", __name__)


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


@patient_bp.route("/api/perfil/paciente/<int:id_usuario>", methods=["GET"])
@require_role("admin", "profesional", "paciente")
def get_perfil_paciente(id_usuario: int):
    auth_error = require_authenticated()
    if auth_error:
        return auth_error

    rol = session.get("rol")
    usuario_id = session.get("idUsuario")

    if rol not in ("admin", "profesional") and int(usuario_id) != id_usuario:
        return jsonify({"success": False, "message": "No autorizado"}), 403

    payload, status = patient_service.get_patient_profile(id_usuario)
    return jsonify(payload), status


@patient_bp.route("/api/perfil/paciente", methods=["PUT"])
@require_role("paciente")
def editar_perfil_paciente():
    data = request.get_json() or {}
    data["idUsuario"] = session.get("idUsuario")
    payload, status = patient_service.update_patient_profile(data)
    return jsonify(payload), status


@patient_bp.route("/api/perfil/foto", methods=["POST"])
@require_role("paciente")
def actualizar_foto_perfil():
    file = request.files.get("foto") or request.files.get("fotoPerfil")
    payload, status = patient_service.update_profile_photo(session.get("idUsuario"), file)
    if payload.get("success"):
        session["fotoPerfil"] = payload.get("fotoPerfil")
        if session.get("usuario"):
            session["usuario"]["fotoPerfil"] = payload.get("fotoPerfil")
    return jsonify(payload), status


@patient_bp.route("/api/evolucion", methods=["POST"])
@require_role("paciente")
def guardar_evolucion():
    payload, status = patient_service.save_evolution(session.get("idUsuario"), request.get_json() or {})
    return jsonify(payload), status


@patient_bp.route("/api/evolucion", methods=["GET"])
@require_role("paciente")
def historial_evolucion():
    payload, status = patient_service.get_evolution_history(session.get("idUsuario"))
    return jsonify(payload), status


@patient_bp.route("/api/pacientes", methods=["GET"])
@require_role("profesional", "admin")
def listar_pacientes():
    page, limit = _get_pagination()
    payload, status = patient_service.list_patients(page, limit)
    return jsonify(payload), status


@patient_bp.route("/api/profesionales", methods=["GET"])
@require_role("paciente", "profesional", "admin")
def listar_profesionales():
    payload, status = patient_service.list_professionals()
    return jsonify(payload), status


@patient_bp.route("/api/chatbot/enviar", methods=["POST"])
@require_role("paciente")
def enviar_chatbot():
    data = request.get_json() or {}
    payload, status = chatbot_service.build_response(
        session.get("idUsuario"),
        data.get("mensaje"),
    )
    return jsonify(payload), status


@patient_bp.route("/api/chatbot/config", methods=["GET"])
@require_role("paciente")
def get_chatbot_config_paciente():
    config = chatbot_config_service.get_config()
    return jsonify({
        "success": True,
        "config": {
            "max_tokens": config.get("max_tokens", 420)
        }
    }), 200


@patient_bp.route("/api/chatbot/config/events", methods=["GET"])
@require_role("paciente")
def chatbot_config_events_stream():
    queue = chatbot_config_events.subscribe()

    def stream():
        try:
            yield ": conectado\n\n"
            while True:
                try:
                    event = queue.get(timeout=60)
                    yield f"event: chatbot-config\ndata: {event}\n\n"
                except Empty:
                    yield ": keep-alive\n\n"
        finally:
            chatbot_config_events.unsubscribe(queue)

    return Response(stream_with_context(stream()), mimetype="text/event-stream")


@patient_bp.route("/api/paciente/consentimiento-chatbot", methods=["GET"])
@require_role("paciente")
def get_consentimiento_chatbot():
    payload, status = patient_service.get_chatbot_consent(session.get("idUsuario"))
    return jsonify(payload), status


@patient_bp.route("/api/paciente/consentimiento-chatbot", methods=["POST"])
@require_role("paciente")
def update_consentimiento_chatbot():
    data = request.get_json() or {}
    consent = bool(data.get("consentimiento_chatbot"))
    payload, status = patient_service.update_chatbot_consent(session.get("idUsuario"), consent)
    return jsonify(payload), status


@patient_bp.route("/api/chatbot/encuesta", methods=["POST"])
@require_role("paciente")
def guardar_encuesta_chatbot():
    payload, status = patient_service.save_chatbot_survey(session.get("idUsuario"), request.get_json() or {})
    return jsonify(payload), status


@patient_bp.route("/api/chatbot/historial", methods=["GET"])
@require_role("paciente")
def historial_chatbot():
    import logging
    logger = logging.getLogger(__name__)
    patient_id = session.get("idUsuario")
    logger.info(f"historial_chatbot - session idUsuario: {patient_id}, session: {dict(session)}")
    if not patient_id:
        return jsonify({"success": False, "message": "No hay sesión"}), 401
    payload, status = chatbot_service.get_history(patient_id)
    return jsonify(payload), status


@patient_bp.route("/api/chatbot/historial", methods=["DELETE"])
@require_role("paciente")
def eliminar_historial_chatbot():
    from app.repositories import chat_repository
    chat_repository.delete_history(session.get("idUsuario"))
    return jsonify({"success": True}), 200
