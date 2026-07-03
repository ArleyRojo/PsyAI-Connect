import os
from queue import Empty

from flask import Blueprint, Response, current_app, jsonify, request, session, stream_with_context
from flask.views import MethodView

from app.services.patient_service import PatientService
from app.services.chatbot_service import ChatbotService
from app.services.mensajes_service import MensajesService
from app.services.chatbot_config_service import ChatbotConfigService
from app.services.chatbot_config_events import chatbot_config_events
from app.services.documento_service import DocumentoService
from app.utils.route_helpers import RouteHelpers


patient_bp = Blueprint("patient", __name__)
patient_service = PatientService()
chatbot_service = ChatbotService()
mensajes_service = MensajesService()
chatbot_config_service = ChatbotConfigService()
documento_service = DocumentoService()


class PerfilPacienteResource(MethodView):
    def get(self, id_usuario):
        err = RouteHelpers.check_authenticated()
        if err:
            return err
        rol = session.get("rol")
        usuario_id = session.get("idUsuario")
        if rol not in ("admin", "profesional") and int(usuario_id) != id_usuario:
            return jsonify({"success": False, "message": "No autorizado"}), 403
        payload, status = patient_service.get_patient_profile(id_usuario)
        return jsonify(payload), status

    def put(self, id_usuario=None):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        data = request.get_json() or {}
        data["idUsuario"] = session.get("idUsuario")
        payload, status = patient_service.update_patient_profile(data)
        return jsonify(payload), status


class PerfilFotoResource(MethodView):
    def _handle_foto(self):
        err = RouteHelpers.check_authenticated()
        if err:
            return err
        file = request.files.get("foto") or request.files.get("fotoPerfil")
        payload, status = patient_service.update_profile_photo(session.get("idUsuario"), file)
        if payload.get("success"):
            session["fotoPerfil"] = payload.get("fotoPerfil")
            if session.get("usuario"):
                session["usuario"]["fotoPerfil"] = payload.get("fotoPerfil")
        return jsonify(payload), status

    def put(self):
        return self._handle_foto()

    def post(self):
        return self._handle_foto()


class EvolucionResource(MethodView):
    def get(self):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        payload, status = patient_service.get_evolution_history(session.get("idUsuario"))
        return jsonify(payload), status

    def post(self):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        payload, status = patient_service.save_evolution(session.get("idUsuario"), request.get_json() or {})
        return jsonify(payload), status


class PacienteResource(MethodView):
    def get(self):
        rol = session.get("rol")
        if rol not in ("profesional", "admin"):
            return jsonify({"success": False, "message": "No autorizado"}), 403
        page, limit = RouteHelpers.get_pagination()
        payload, status = patient_service.list_patients(page, limit)
        return jsonify(payload), status


class ProfesionalResource(MethodView):
    def get(self):
        err = RouteHelpers.check_authenticated()
        if err:
            return err
        payload, status = patient_service.list_professionals()
        return jsonify(payload), status


class ChatbotResource(MethodView):
    def post(self):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        data = request.get_json() or {}
        payload, status = chatbot_service.build_response(
            session.get("idUsuario"),
            data.get("mensaje"),
        )
        return jsonify(payload), status

    def get(self):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        import logging
        logger = logging.getLogger(__name__)
        patient_id = session.get("idUsuario")
        logger.info(f"historial_chatbot - session idUsuario: {patient_id}, session: {dict(session)}")
        if not patient_id:
            return jsonify({"success": False, "message": "No hay sesión"}), 401
        payload, status = chatbot_service.get_history(patient_id)
        return jsonify(payload), status

    def delete(self):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        mensajes_service.eliminar_historial_chatbot(session.get("idUsuario"))
        return jsonify({"success": True}), 200


class ChatbotEncuestaResource(MethodView):
    def post(self):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        payload, status = patient_service.save_chatbot_survey(session.get("idUsuario"), request.get_json() or {})
        return jsonify(payload), status


class ChatbotConfigResource(MethodView):
    def get(self):
        if "usuario" not in session or session.get("rol") != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 200
        config_data, _ = chatbot_config_service.get_config()
        return jsonify({
            "success": True,
            "config": {
                "max_tokens": config_data.get("config", {}).get("max_tokens", 600),
                "max_tokens_user": config_data.get("config", {}).get("max_tokens_user", 1000),
                "daily_message_limit": config_data.get("config", {}).get("daily_message_limit", 20),
            }
        }), 200


class ChatbotConfigEventsResource(MethodView):
    def get(self):
        if "usuario" not in session or session.get("rol") != "paciente":
            def error_stream():
                yield "event: auth-error\ndata: {\"message\": \"No autorizado\"}\n\n"
            return Response(
                stream_with_context(error_stream()),
                mimetype="text/event-stream",
                status=200,
            )

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


class ConsentimientoChatbotResource(MethodView):
    def get(self):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        payload, status = patient_service.get_chatbot_consent(session.get("idUsuario"))
        return jsonify(payload), status

    def post(self):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        data = request.get_json() or {}
        consent = bool(data.get("consentimiento_chatbot"))
        payload, status = patient_service.update_chatbot_consent(session.get("idUsuario"), consent)
        return jsonify(payload), status


class DocumentoPacienteResource(MethodView):
    def get(self):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        payload = documento_service.list_patient_dashboard(session.get("idUsuario"))
        return jsonify(payload), (200 if payload.get("success") else 500)

    def post(self):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        file = request.files.get("archivo")
        descripcion = request.form.get("descripcion", "")
        payload, status = documento_service.upload_patient_doc(session.get("idUsuario"), file, descripcion)
        return jsonify(payload), status

    def delete(self, id_documento):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        payload, status = documento_service.delete_patient_doc(id_documento, session.get("idUsuario"))
        return jsonify(payload), status

    def patch(self, id_documento):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        data = request.get_json() or {}
        professional_id = data.get("profesionalId") or request.args.get("profesionalId", type=int)
        autorizar = data.get("autorizar")
        if not professional_id and autorizar is None:
            return jsonify({"success": False, "message": "Falta profesionalId o autorizar"}), 400
        if autorizar is None:
            payload, status = documento_service.toggle_autorizacion(
                id_documento, session.get("idUsuario"), professional_id,
            )
        else:
            from app.services.documento_service import DocumentoService
            srv = DocumentoService()
            if autorizar:
                payload, status = srv.autorizar_documento(id_documento, session.get("idUsuario"), professional_id)
            else:
                payload, status = srv.desautorizar_documento(id_documento, session.get("idUsuario"), professional_id)
        return jsonify(payload), status


class ChatContactoResource(MethodView):
    def get(self):
        rol = session.get("rol")
        if rol != "paciente":
            return jsonify({"success": False, "message": "No autorizado"}), 403
        id_paciente = session.get("idUsuario")
        payload, _ = patient_service.list_professionals()
        profesionales = payload.get("profesionales", [])
        upload_dir = os.path.join(current_app.root_path, "static", "uploads")
        for p in profesionales:
            fp = p.get("fotoPerfil")
            if fp and not os.path.exists(os.path.join(upload_dir, fp)):
                p["fotoPerfil"] = None
        resultado = mensajes_service.get_contactos_con_mensajes(id_paciente, profesionales)
        return jsonify({"success": True, "profesionales": resultado}), 200


class ChatMensajeResource(MethodView):
    def get(self):
        err = RouteHelpers.check_authenticated()
        if err:
            return err
        id_receptor = request.args.get("receptor", type=int)
        if not id_receptor:
            return jsonify({"success": False, "message": "Falta receptor"}), 400
        msgs = mensajes_service.get_mensajes(
            session.get("idUsuario"), id_receptor,
            request.args.get("desde", default=0, type=int),
        )
        return jsonify({"success": True, "mensajes": msgs}), 200

    def post(self):
        err = RouteHelpers.check_authenticated()
        if err:
            return err
        data = request.get_json() or {}
        receptor = data.get("receptor")
        mensaje = (data.get("mensaje") or "").strip()
        if not receptor or not mensaje:
            return jsonify({"success": False, "message": "Datos incompletos"}), 400
        if len(mensaje) > 2000:
            return jsonify({"success": False, "message": "Mensaje demasiado largo"}), 400
        id_msg = mensajes_service.enviar_mensaje(session.get("idUsuario"), receptor, mensaje)
        return jsonify({"success": True, "idMensaje": id_msg}), 201


patient_bp.add_url_rule("/api/perfil/paciente/<int:id_usuario>", view_func=PerfilPacienteResource.as_view("perfil_paciente"))
patient_bp.add_url_rule("/api/perfil/paciente", view_func=PerfilPacienteResource.as_view("perfil_paciente_update"))
patient_bp.add_url_rule("/api/perfil/paciente/foto", view_func=PerfilFotoResource.as_view("perfil_foto"))
patient_bp.add_url_rule("/api/evolucion", view_func=EvolucionResource.as_view("evolucion"))
patient_bp.add_url_rule("/api/pacientes", view_func=PacienteResource.as_view("pacientes"))
patient_bp.add_url_rule("/api/profesionales", view_func=ProfesionalResource.as_view("profesionales"))
patient_bp.add_url_rule("/api/chatbot", view_func=ChatbotResource.as_view("chatbot"))
patient_bp.add_url_rule("/api/chatbot/historial", view_func=ChatbotResource.as_view("chatbot_historial"))
patient_bp.add_url_rule("/api/chatbot/encuesta", view_func=ChatbotEncuestaResource.as_view("chatbot_encuesta"))
patient_bp.add_url_rule("/api/chatbot/config", view_func=ChatbotConfigResource.as_view("chatbot_config"))
patient_bp.add_url_rule("/api/chatbot/config/events", view_func=ChatbotConfigEventsResource.as_view("chatbot_config_events"))
patient_bp.add_url_rule("/api/paciente/consentimiento-chatbot", view_func=ConsentimientoChatbotResource.as_view("consentimiento_chatbot"))
patient_bp.add_url_rule("/api/paciente/documentos", view_func=DocumentoPacienteResource.as_view("documentos_paciente"))
patient_bp.add_url_rule("/api/paciente/documentos/subir", view_func=DocumentoPacienteResource.as_view("documento_subir"))
patient_bp.add_url_rule("/api/paciente/documentos/<int:id_documento>", view_func=DocumentoPacienteResource.as_view("documento_paciente"))
patient_bp.add_url_rule("/api/chat/contactos", view_func=ChatContactoResource.as_view("chat_contactos"))
patient_bp.add_url_rule("/api/chat/mensajes", view_func=ChatMensajeResource.as_view("chat_mensajes"))
# Legacy aliases (backward compat)
patient_bp.add_url_rule("/api/chatbot/enviar", view_func=ChatbotResource.as_view("chatbot_enviar_legacy"))
patient_bp.add_url_rule("/api/perfil/foto", view_func=PerfilFotoResource.as_view("perfil_foto_legacy"))
patient_bp.add_url_rule("/api/chat/profesionales", view_func=ChatContactoResource.as_view("chat_profesionales_legacy"))
patient_bp.add_url_rule("/api/paciente/chat/mensajes", view_func=ChatMensajeResource.as_view("chat_mensajes_paciente_legacy"))
patient_bp.add_url_rule("/api/chat/enviar", view_func=ChatMensajeResource.as_view("chat_enviar_legacy"))
patient_bp.add_url_rule("/api/paciente/chat/enviar", view_func=ChatMensajeResource.as_view("chat_paciente_enviar_legacy"))
