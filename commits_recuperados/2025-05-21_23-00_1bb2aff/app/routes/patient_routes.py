from queue import Empty

from flask import Blueprint, Response, jsonify, request, session, stream_with_context

from app.repositories import mensajes_repository
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
            "max_tokens": config.get("max_tokens", 420),
            "daily_message_limit": config.get("daily_message_limit", 20),
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


# -- MENSAJERIA DIRECTA -------------------------------------------------
@patient_bp.route("/api/chat/profesionales", methods=["GET"])
@require_role("paciente")
def chat_listar_profesionales():
    """
    Devuelve los profesionales registrados,
    enriquecidos con el ultimo mensaje y no-leidos.
    """
    from app.repositories import patient_repository

    id_paciente = session.get("idUsuario")
    profesionales = patient_repository.list_professionals_for_patient(id_paciente)
    resultado = []

    for profesional in profesionales:
        ultimo = mensajes_repository.get_ultimo_mensaje(id_paciente, profesional["idUsuario"])
        no_leidos = mensajes_repository.contar_no_leidos(id_paciente, profesional["idUsuario"])
        resultado.append({
            **profesional,
            "ultimoMensaje": ultimo["mensaje"][:60] if ultimo else None,
            "ultimaFecha": str(ultimo["fecha"]) if ultimo else None,
            "ultimoIdMensaje": ultimo["idMensaje"] if ultimo else 0,
            "ultimoEmisor": ultimo["idEmisor"] if ultimo else None,
            "noLeidos": no_leidos,
        })

    resultado = _ordenar_contactos_chat(resultado)
    return jsonify({"success": True, "profesionales": resultado}), 200


@patient_bp.route("/api/chat/mensajes", methods=["GET"])
@patient_bp.route("/api/paciente/chat/mensajes", methods=["GET"])
@require_role("paciente", "profesional")
def chat_get_mensajes_paciente():
    id_usuario = session.get("idUsuario")
    id_receptor = request.args.get("receptor", type=int)
    desde_id = request.args.get("desde", default=0, type=int)

    if not id_receptor:
        return jsonify({"success": False, "message": "Falta receptor"}), 400

    mensajes_repository.marcar_leidos(id_usuario, id_receptor)
    rows = mensajes_repository.get_conversacion(id_usuario, id_receptor, desde_id)
    msgs = [
        {**row, "esMio": row["idEmisor"] == id_usuario, "fecha": str(row["fecha"])}
        for row in rows
    ]
    return jsonify({"success": True, "mensajes": msgs}), 200


@patient_bp.route("/api/chat/enviar", methods=["POST"])
@patient_bp.route("/api/paciente/chat/enviar", methods=["POST"])
@require_role("paciente", "profesional")
def chat_enviar_paciente():
    data = request.get_json() or {}
    receptor = data.get("receptor")
    mensaje = (data.get("mensaje") or "").strip()

    if not receptor or not mensaje:
        return jsonify({"success": False, "message": "Datos incompletos"}), 400
    if len(mensaje) > 2000:
        return jsonify({"success": False, "message": "Mensaje demasiado largo"}), 400

    id_msg = mensajes_repository.enviar_mensaje(session.get("idUsuario"), receptor, mensaje)
    return jsonify({"success": True, "idMensaje": id_msg}), 201
