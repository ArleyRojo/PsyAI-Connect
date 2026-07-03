import json
import time as _time

from flask import Blueprint, jsonify, request, session, Response
from flask.views import MethodView

from app.services.admin_service import AdminService
from app.services.chatbot_config_service import ChatbotConfigService
from app.services.chatbot_config_events import chatbot_config_events
from app.services.telemetry_service import (
    telemetry_service,
    _normalize_ip,
    get_active_user_ids,
)
from app.repositories.admin_repository import AdminRepository
from app.utils.route_helpers import RouteHelpers


admin_bp = Blueprint("admin", __name__)
admin_service = AdminService()
chatbot_config_service = ChatbotConfigService()
admin_repo = AdminRepository()


class AdminDiagnosticoResource(MethodView):
    def post(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        payload, status = admin_service.create_report_columns()
        return jsonify(payload), status


class AdminStatsResource(MethodView):
    def get(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        payload, status = admin_service.get_stats()
        return jsonify(payload), status


class AdminStatsStreamResource(MethodView):
    def get(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        client_ip = _normalize_ip(request.remote_addr or "127.0.0.1")
        telemetry_service.sse_connected(client_ip)

        def generate():
            last_version = -1
            last_emit = 0
            poll_count = 0
            try:
                while True:
                    telemetry_service.sse_heartbeat(client_ip)
                    current_version = telemetry_service._version
                    now = _time.time()
                    force = current_version != last_version
                    timed = now - last_emit >= 5
                    if force or timed:
                        last_version = current_version
                        last_emit = now
                        payload, _ = admin_service.get_stats(force=force)
                        yield f"data: {json.dumps(payload)}\n\n"
                        poll_count = 0
                    else:
                        poll_count += 1
                        if poll_count >= 4:
                            yield ": heartbeat\n\n"
                    _time.sleep(1)
            finally:
                telemetry_service.sse_disconnected(client_ip)

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )


class AdminLogsStreamResource(MethodView):
    def get(self):
        err = RouteHelpers.check_admin()
        if err:
            def _empty():
                while True:
                    yield ": keepalive\n\n"
                    _time.sleep(30)
            return Response(_empty(), mimetype="text/event-stream")

        def generate():
            last_version = -1
            while True:
                current_version = AdminRepository.get_logs_version()
                if current_version != last_version:
                    last_version = current_version
                    logs = admin_repo.get_logs(limit=10)
                    logs.sort(key=lambda x: x["fecha"], reverse=True)
                    yield f"data: {json.dumps({'success': True, 'logs': logs})}\n\n"
                _time.sleep(0.5)

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )


class AdminUsuarioResource(MethodView):
    def get(self, id_usuario=None):
        err = RouteHelpers.check_admin()
        if err:
            return err
        if id_usuario:
            payload, status = admin_service.get_user(id_usuario)
        else:
            page, limit = RouteHelpers.get_pagination()
            payload, status = admin_service.list_users(page, limit)
        return jsonify(payload), status

    def post(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        payload, status = admin_service.create_user(request.get_json() or {})
        return jsonify(payload), status

    def put(self, id_usuario):
        err = RouteHelpers.check_admin()
        if err:
            return err
        data = request.get_json() or {}
        data["idUsuario"] = id_usuario
        payload, status = admin_service.update_user(data)
        return jsonify(payload), status

    def patch(self, id_usuario):
        err = RouteHelpers.check_admin()
        if err:
            return err
        data = request.get_json() or {}
        if data.get("bloquear") is not None or data.get("estadoBloqueo") is not None:
            data["idUsuario"] = id_usuario
            payload, status = admin_service.block_user(data)
        elif data.get("rol"):
            data["idUsuario"] = id_usuario
            payload, status = admin_service.change_role(data)
        else:
            return jsonify({"success": False, "message": "Acción no especificada (bloquear o rol)"}), 400
        return jsonify(payload), status

    def delete(self, id_usuario):
        err = RouteHelpers.check_admin()
        if err:
            return err
        payload, status = admin_service.delete_user(id_usuario)
        return jsonify(payload), status


class AdminRolResource(MethodView):
    def get(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        filter_param = request.args.get("filter", "")
        if filter_param == "historial":
            payload, status = admin_service.role_history()
        else:
            payload, status = admin_service.list_role_users()
        return jsonify(payload), status


class AdminNotificacionResource(MethodView):
    def get(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        payload, status = admin_service.notifications_feed()
        return jsonify(payload), status

    def post(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        payload, status = admin_service.create_notification(request.get_json() or {})
        return jsonify(payload), status

    def delete(self, id_notificacion=None):
        if not id_notificacion:
            return jsonify({"success": False, "message": "Falta id de notificación"}), 400
        err = RouteHelpers.check_admin()
        if err:
            return err
        payload, status = admin_service.delete_notification(id_notificacion)
        return jsonify(payload), status


class AdminLogResource(MethodView):
    def get(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        payload, status = admin_service.get_logs()
        return jsonify(payload), status


class AdminOnlineResource(MethodView):
    def get(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        ids = get_active_user_ids()
        usuarios = admin_repo.get_users_by_ids(ids)
        return jsonify({"success": True, "usuarios": usuarios, "total": len(usuarios)}), 200


class AdminChatbotConfigResource(MethodView):
    def get(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        payload = chatbot_config_service.get_config()
        return jsonify({"success": True, "config": payload}), 200

    def put(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        data = request.get_json() or {}
        admin_id = session.get("idUsuario")
        payload, status = chatbot_config_service.save_config(data, admin_id)
        if status < 400 and payload.get("success"):
            chatbot_config_events.publish_config_update({
                "max_tokens": data.get("max_tokens"),
                "max_tokens_user": data.get("max_tokens_user"),
                "daily_message_limit": data.get("daily_message_limit"),
            })
        return jsonify(payload), status

    def patch(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        admin_id = session.get("idUsuario")
        data = request.get_json() or {}
        risk_terms_str = data.get("risk_terms")
        if risk_terms_str is not None:
            body, status = chatbot_config_service.save_risk_terms(risk_terms_str, admin_id)
            return jsonify(body), status
        return jsonify({"success": False, "message": "Falta risk_terms en el body"}), 400

    def delete(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        admin_id = session.get("idUsuario")
        body, status = chatbot_config_service.clear_risk_terms(admin_id)
        return jsonify(body), status


class AdminChatbotPalabrasResource(MethodView):
    def get(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        palabras = chatbot_config_service.get_historial_palabras_riesgo()
        return jsonify({"success": True, "palabras": palabras}), 200


class AdminChatbotHistorialResource(MethodView):
    def get(self):
        err = RouteHelpers.check_admin()
        if err:
            return err
        nivel = request.args.get("nivel", "")
        search = request.args.get("q", "")
        payload, status = admin_service.get_chatbot_historial(nivel, search)
        return jsonify(payload), status


admin_bp.add_url_rule("/api/admin/crear-columnas-diagnostico", view_func=AdminDiagnosticoResource.as_view("admin_diagnostico"))
admin_bp.add_url_rule("/api/admin/stats", view_func=AdminStatsResource.as_view("admin_stats"))
admin_bp.add_url_rule("/api/admin/stats/stream", view_func=AdminStatsStreamResource.as_view("admin_stats_stream"))
admin_bp.add_url_rule("/api/admin/logs/stream", view_func=AdminLogsStreamResource.as_view("admin_logs_stream"))
admin_bp.add_url_rule("/api/admin/usuarios", view_func=AdminUsuarioResource.as_view("admin_usuarios"))
admin_bp.add_url_rule("/api/admin/usuarios/<int:id_usuario>", view_func=AdminUsuarioResource.as_view("admin_usuario"))
admin_bp.add_url_rule("/api/admin/roles/usuarios", view_func=AdminRolResource.as_view("admin_roles_usuarios"))
admin_bp.add_url_rule("/api/admin/roles/historial", view_func=AdminRolResource.as_view("admin_roles_historial"))
admin_bp.add_url_rule("/api/admin/notificaciones", view_func=AdminNotificacionResource.as_view("admin_notificaciones"))
admin_bp.add_url_rule("/api/admin/notificaciones/<int:id_notificacion>", view_func=AdminNotificacionResource.as_view("admin_notificacion"))
admin_bp.add_url_rule("/api/admin/logs", view_func=AdminLogResource.as_view("admin_logs"))
admin_bp.add_url_rule("/api/admin/online", view_func=AdminOnlineResource.as_view("admin_online"))
admin_bp.add_url_rule("/api/admin/chatbot-config", view_func=AdminChatbotConfigResource.as_view("admin_chatbot_config"))
admin_bp.add_url_rule("/api/admin/chatbot-config/palabras-detectadas", view_func=AdminChatbotPalabrasResource.as_view("admin_chatbot_palabras"))
admin_bp.add_url_rule("/api/admin/chatbot-historial", view_func=AdminChatbotHistorialResource.as_view("admin_chatbot_historial"))
# Legacy aliases
admin_bp.add_url_rule("/api/admin/usuarios/<int:id_usuario>/bloquear", view_func=AdminUsuarioResource.as_view("admin_usuario_bloquear_legacy"))
admin_bp.add_url_rule("/api/admin/usuarios/<int:id_usuario>/rol", view_func=AdminUsuarioResource.as_view("admin_usuario_rol_legacy"))
admin_bp.add_url_rule("/api/admin/usuarios-online", view_func=AdminOnlineResource.as_view("admin_usuarios_online_legacy"))
admin_bp.add_url_rule("/api/admin/chatbot-config/clear-risk-terms", view_func=AdminChatbotConfigResource.as_view("admin_chatbot_clear_risk_legacy"))
admin_bp.add_url_rule("/api/admin/chatbot-risk-terms", view_func=AdminChatbotConfigResource.as_view("admin_chatbot_risk_terms_legacy"))
admin_bp.add_url_rule("/api/admin/chatbot-detected-words", view_func=AdminChatbotPalabrasResource.as_view("admin_chatbot_detected_words_legacy"))
