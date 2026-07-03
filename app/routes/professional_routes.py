import os

from flask import Blueprint, current_app, jsonify, request, session, send_file
from flask.views import MethodView

from app.services.professional_service import ProfessionalService
from app.services.mensajes_service import MensajesService
from app.services.documento_service import DocumentoService
from app.utils.route_helpers import RouteHelpers


professional_bp = Blueprint("professional", __name__)
professional_service = ProfessionalService()
mensajes_service = MensajesService()
documento_service = DocumentoService()


class PerfilProfesionalResource(MethodView):
    def get(self, id_usuario):
        err = RouteHelpers.check_role("admin", "profesional", "paciente")
        if err:
            return err
        payload, status = professional_service.get_profile(id_usuario)
        return jsonify(payload), status

    def put(self):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        data = request.get_json() or {}
        user_id = session.get("idUsuario")
        if data.get("idUsuario") and data["idUsuario"] != user_id:
            return jsonify({"success": False, "message": "No tienes permiso para editar este perfil"}), 403
        data["idUsuario"] = user_id
        payload, status = professional_service.update_profile(data)
        return jsonify(payload), status


class DisponibilidadResource(MethodView):
    def post(self):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        payload, status = professional_service.create_availability(session.get("idUsuario"), request.get_json() or {})
        return jsonify(payload), status

    def get(self, id_profesional=None):
        err = RouteHelpers.check_role("admin", "profesional", "paciente")
        if err:
            return err
        if not id_profesional:
            id_profesional = session.get("idUsuario")
        payload, status = professional_service.get_availability(id_profesional)
        return jsonify(payload), status


class DashboardResource(MethodView):
    def get(self):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        payload, status = professional_service.get_dashboard(session.get("idUsuario"))
        return jsonify(payload), status


class ProfesionalPacienteResource(MethodView):
    def get(self):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        payload, status = professional_service.list_patients(session.get("idUsuario"))
        return jsonify(payload), status


class DiagnosticoResource(MethodView):
    def get(self):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        payload, status = professional_service.diagnosis_history(session.get("idUsuario"))
        return jsonify(payload), status

    def post(self):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        payload, status = professional_service.save_diagnosis(session.get("idUsuario"), request.get_json() or {})
        return jsonify(payload), status


class ReporteResource(MethodView):
    def get(self, **kwargs):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        filter_param = request.args.get("filter", "")
        if filter_param == "eliminados":
            payload, status = professional_service.get_deleted_reports(session.get("idUsuario"))
        else:
            payload, status = professional_service.report_overview(session.get("idUsuario"))
        return jsonify(payload), status

    def post(self):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        payload, status = professional_service.create_report(session.get("idUsuario"), request.get_json() or {})
        return jsonify(payload), status

    def put(self, id_reporte):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        data = request.get_json() or {}
        data["idReporte"] = id_reporte
        payload, status = professional_service.update_report(session.get("idUsuario"), data)
        return jsonify(payload), status

    def delete(self, id_reporte):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        payload, status = professional_service.delete_report(session.get("idUsuario"), id_reporte)
        return jsonify(payload), status


class EvolucionProfesionalResource(MethodView):
    def get(self):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        payload, status = professional_service.all_evolution(session.get("idUsuario"))
        return jsonify(payload), status


class PacienteChatbotHistorialResource(MethodView):
    def get(self, id_paciente):
        err = RouteHelpers.check_role("profesional", "admin")
        if err:
            return err
        payload, status = professional_service.get_patient_chatbot_history(session.get("idUsuario"), id_paciente)
        return jsonify(payload), status


class DocumentoProfesionalPacienteResource(MethodView):
    def get(self, id_paciente):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        payload = documento_service.list_patient_docs(session.get("idUsuario"), id_paciente)
        return jsonify(payload), (200 if payload.get("success") else 500)

    def post(self, id_paciente):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        file = request.files.get("archivo")
        categoria = request.form.get("categoria", "Otro")
        visibilidad = request.form.get("visibilidad", "privado")
        notas = request.form.get("notas", "")
        payload, status = documento_service.upload_profesional_doc(
            session.get("idUsuario"), id_paciente, file, categoria, visibilidad, notas,
        )
        return jsonify(payload), status

    def _handle_visibilidad(self, id_documento):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        data = request.get_json() or {}
        visibilidad = data.get("visibilidad")
        if visibilidad:
            payload, status = documento_service.toggle_doc_visibility(id_documento, session.get("idUsuario"))
        else:
            return jsonify({"success": False, "message": "Falta visibilidad"}), 400
        return jsonify(payload), status

    def patch(self, id_documento):
        return self._handle_visibilidad(id_documento)

    def put(self, id_documento):
        return self._handle_visibilidad(id_documento)

    def delete(self, id_documento):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        payload, status = documento_service.delete_profesional_doc(id_documento, session.get("idUsuario"))
        return jsonify(payload), status


class DownloadResource(MethodView):
    def _send(self, tipo, id_documento):
        err = RouteHelpers.check_authenticated()
        if err:
            return err
        if tipo in ("profesional", "documento-profesional"):
            err = RouteHelpers.check_role("profesional")
            if err:
                return err
            doc, err_payload, status = documento_service.get_profesional_doc_for_download(
                id_documento, session.get("idUsuario"),
            )
        elif tipo in ("paciente", "documento-paciente"):
            err = RouteHelpers.check_role("profesional", "paciente")
            if err:
                return err
            doc, err_payload, status = documento_service.get_patient_doc_for_download(
                id_documento, session.get("idUsuario"), session.get("rol"),
            )
        else:
            return jsonify({"success": False, "message": "Tipo inválido"}), 400
        if err_payload:
            return jsonify(err_payload), status
        path = os.path.join(current_app.root_path, "static", doc["rutaArchivo"])
        if not os.path.exists(path):
            return jsonify({"success": False, "message": "Archivo no encontrado en el servidor"}), 404
        return send_file(path, download_name=doc["nombreArchivo"], as_attachment=False)

    def get(self, id_documento, tipo=None):
        if tipo is None:
            path = request.path
            if "/documento-profesional/" in path:
                tipo = "documento-profesional"
            elif "/documento-paciente/" in path:
                tipo = "documento-paciente"
            else:
                return jsonify({"success": False, "message": "Tipo de descarga no especificado"}), 400
        return self._send(tipo, id_documento)


class ChatContactoProfesionalResource(MethodView):
    def get(self):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        id_profesional = session.get("idUsuario")
        pacientes = professional_service.list_patients_for_chat()
        resultado = mensajes_service.get_contactos_con_mensajes(id_profesional, pacientes, id_field="idUsuario")
        return jsonify({"success": True, "pacientes": resultado}), 200


class ChatMensajeProfesionalResource(MethodView):
    def get(self):
        err = RouteHelpers.check_authenticated()
        if err:
            return err
        id_paciente = request.args.get("receptor", type=int)
        if not id_paciente:
            return jsonify({"success": False, "message": "Falta receptor"}), 400
        msgs = mensajes_service.get_mensajes(
            session.get("idUsuario"), id_paciente,
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


professional_bp.add_url_rule("/api/perfil/profesional/<int:id_usuario>", view_func=PerfilProfesionalResource.as_view("perfil_profesional"))
professional_bp.add_url_rule("/api/perfil/profesional", view_func=PerfilProfesionalResource.as_view("perfil_profesional_update"))
professional_bp.add_url_rule("/api/disponibilidad", view_func=DisponibilidadResource.as_view("disponibilidad_crear"))
professional_bp.add_url_rule("/api/disponibilidad/<int:id_profesional>", view_func=DisponibilidadResource.as_view("disponibilidad_ver"))
professional_bp.add_url_rule("/api/profesional/dashboard", view_func=DashboardResource.as_view("dashboard"))
professional_bp.add_url_rule("/api/profesional/pacientes", view_func=ProfesionalPacienteResource.as_view("profesional_pacientes"))
professional_bp.add_url_rule("/api/diagnosticos", view_func=DiagnosticoResource.as_view("diagnosticos"))
professional_bp.add_url_rule("/api/reportes", view_func=ReporteResource.as_view("reportes"))
professional_bp.add_url_rule("/api/reportes/<int:id_reporte>", view_func=ReporteResource.as_view("reporte"))
professional_bp.add_url_rule("/api/evolucion/profesional", view_func=EvolucionProfesionalResource.as_view("evolucion_profesional"))
professional_bp.add_url_rule("/api/profesional/pacientes/<int:id_paciente>/chatbot/historial", view_func=PacienteChatbotHistorialResource.as_view("paciente_chatbot_historial"))
professional_bp.add_url_rule("/api/profesional/pacientes/<int:id_paciente>/documentos", view_func=DocumentoProfesionalPacienteResource.as_view("documentos_profesional_paciente"))
professional_bp.add_url_rule("/api/profesional/documentos/<int:id_documento>", view_func=DocumentoProfesionalPacienteResource.as_view("documento_profesional"))
professional_bp.add_url_rule("/api/descargar/<tipo>/<int:id_documento>", view_func=DownloadResource.as_view("descargar"))
professional_bp.add_url_rule("/api/chat/pacientes", view_func=ChatContactoProfesionalResource.as_view("chat_contactos_profesional"))
professional_bp.add_url_rule("/api/profesional/chat/mensajes", view_func=ChatMensajeProfesionalResource.as_view("chat_mensajes_profesional"))
professional_bp.add_url_rule("/api/profesional/chat/enviar", view_func=ChatMensajeProfesionalResource.as_view("chat_enviar_profesional"))
# Legacy aliases
professional_bp.add_url_rule("/api/reportes/profesional", view_func=ReporteResource.as_view("reportes_profesional_legacy"))
professional_bp.add_url_rule("/api/reportes/eliminados", view_func=ReporteResource.as_view("reportes_eliminados_legacy"))
professional_bp.add_url_rule("/api/profesional/paciente/<int:id_paciente>/chatbot-historial", view_func=PacienteChatbotHistorialResource.as_view("paciente_chatbot_historial_legacy"))
professional_bp.add_url_rule("/api/profesional/paciente/<int:id_paciente>/documentos", view_func=DocumentoProfesionalPacienteResource.as_view("documentos_profesional_paciente_legacy"))
professional_bp.add_url_rule("/api/profesional/documentos/<int:id_documento>/visibilidad", view_func=DocumentoProfesionalPacienteResource.as_view("documento_visibilidad_legacy"))
professional_bp.add_url_rule("/api/descargar/documento-profesional/<int:id_documento>", view_func=DownloadResource.as_view("descargar_profesional_legacy"))
professional_bp.add_url_rule("/api/descargar/documento-paciente/<int:id_documento>", view_func=DownloadResource.as_view("descargar_paciente_legacy"))
