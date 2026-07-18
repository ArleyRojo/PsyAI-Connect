import json
import time as _time

from django.http import JsonResponse, StreamingHttpResponse
from django.views import View

from apps.admin_panel.services import (
    AdminService,
    telemetry_service,
    _normalize_ip,
    get_active_user_ids,
)
from apps.core.permissions import require_role
from apps.admin_panel.repositories import AdminRepository

admin_service = AdminService()
admin_repo = AdminRepository()


class AdminDiagnosticoView(View):
    def post(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        payload, status = admin_service.create_report_columns()
        return JsonResponse(payload, status=status)


class AdminStatsView(View):
    def get(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        payload, status = admin_service.get_stats()
        return JsonResponse(payload, status=status)


class AdminStatsStreamView(View):
    def get(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err

        client_ip = _normalize_ip(request.META.get("REMOTE_ADDR", "127.0.0.1"))
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

        response = StreamingHttpResponse(
            generate(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class AdminLogsStreamView(View):
    def get(self, request):
        user, err = require_role(request, "admin")
        if err:
            def _empty():
                while True:
                    yield ": keepalive\n\n"
                    _time.sleep(30)
            response = StreamingHttpResponse(_empty(), content_type="text/event-stream")
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"
            return response

        def generate():
            last_version = -1
            while True:
                current_version = AdminRepository.get_logs_version()
                if current_version != last_version:
                    last_version = current_version
                    logs = admin_repo.get_logs(limit=10)
                    logs.sort(key=lambda x: x.get("fecha", ""), reverse=True)
                    yield f"data: {json.dumps({'success': True, 'logs': logs})}\n\n"
                _time.sleep(0.5)

        response = StreamingHttpResponse(
            generate(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class AdminUsuarioView(View):
    def get(self, request, id_usuario=None):
        user, err = require_role(request, "admin")
        if err:
            return err
        if id_usuario:
            payload, status = admin_service.get_user(id_usuario)
        else:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            payload, status = admin_service.list_users(page, limit)
        return JsonResponse(payload, status=status)

    def post(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            data = {}
        payload, status = admin_service.create_user(data)
        return JsonResponse(payload, status=status)

    def put(self, request, id_usuario):
        user, err = require_role(request, "admin")
        if err:
            return err
        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            data = {}
        data["idUsuario"] = id_usuario
        payload, status = admin_service.update_user(data)
        return JsonResponse(payload, status=status)

    def patch(self, request, id_usuario):
        user, err = require_role(request, "admin")
        if err:
            return err
        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            data = {}
        if data.get("bloquear") is not None or data.get("estadoBloqueo") is not None:
            data["idUsuario"] = id_usuario
            payload, status = admin_service.block_user(data)
        elif data.get("rol"):
            data["idUsuario"] = id_usuario
            payload, status = admin_service.change_role(data)
        else:
            return JsonResponse({"success": False, "message": "Acción no especificada (bloquear o rol)"}, status=400)
        return JsonResponse(payload, status=status)

    def delete(self, request, id_usuario):
        user, err = require_role(request, "admin")
        if err:
            return err
        payload, status = admin_service.delete_user(id_usuario)
        return JsonResponse(payload, status=status)


class AdminRolView(View):
    def get(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        filter_param = request.GET.get("filter", "")
        if filter_param == "historial":
            payload, status = admin_service.role_history()
        else:
            payload, status = admin_service.list_role_users()
        return JsonResponse(payload, status=status)


class AdminNotificacionView(View):
    def get(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        payload, status = admin_service.notifications_feed()
        return JsonResponse(payload, status=status)

    def post(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            data = {}
        payload, status = admin_service.create_notification(data)
        return JsonResponse(payload, status=status)

    def delete(self, request, id_notificacion=None):
        if not id_notificacion:
            return JsonResponse({"success": False, "message": "Falta id de notificación"}, status=400)
        user, err = require_role(request, "admin")
        if err:
            return err
        payload, status = admin_service.delete_notification(id_notificacion)
        return JsonResponse(payload, status=status)


class AdminLogView(View):
    def get(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        payload, status = admin_service.get_logs()
        return JsonResponse(payload, status=status)


class AdminOnlineView(View):
    def get(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        ids = get_active_user_ids()
        usuarios = admin_repo.get_users_by_ids(ids)
        return JsonResponse({"success": True, "usuarios": usuarios, "total": len(usuarios)}, status=200)


class AdminChatbotHistorialView(View):
    def get(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        nivel = request.GET.get("nivel", "")
        search = request.GET.get("q", "")
        payload, status = admin_service.get_chatbot_historial(nivel, search)
        return JsonResponse(payload, status=status)


class AdminChatbotConfigView(View):
    def get(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        from apps.chatbot.services import ChatbotConfigService
        chatbot_config_service = ChatbotConfigService()
        payload = chatbot_config_service.get_config()
        return JsonResponse({"success": True, "config": payload}, status=200)

    def put(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        from apps.chatbot.services import ChatbotConfigService, ChatbotConfigEventsService
        chatbot_config_service = ChatbotConfigService()
        chatbot_config_events = ChatbotConfigEventsService()
        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            data = {}
        admin_id = request.session.get("idUsuario")
        payload, status = chatbot_config_service.save_config(data, admin_id)
        if status < 400 and payload.get("success"):
            chatbot_config_events.publish_config_update({
                "max_tokens": data.get("max_tokens"),
                "max_tokens_user": data.get("max_tokens_user"),
                "daily_message_limit": data.get("daily_message_limit"),
            })
        return JsonResponse(payload, status=status)

    def patch(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        from apps.chatbot.services import ChatbotConfigService
        chatbot_config_service = ChatbotConfigService()
        admin_id = request.session.get("idUsuario")
        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            data = {}
        risk_terms_str = data.get("risk_terms")
        if risk_terms_str is not None:
            body, status = chatbot_config_service.save_risk_terms(risk_terms_str, admin_id)
            return JsonResponse(body, status=status)
        return JsonResponse({"success": False, "message": "Falta risk_terms en el body"}, status=400)

    def delete(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        from apps.chatbot.services import ChatbotConfigService
        chatbot_config_service = ChatbotConfigService()
        admin_id = request.session.get("idUsuario")
        body, status = chatbot_config_service.clear_risk_terms(admin_id)
        return JsonResponse(body, status=status)


class AdminChatbotPalabrasView(View):
    def get(self, request):
        user, err = require_role(request, "admin")
        if err:
            return err
        from apps.chatbot.services import ChatbotConfigService
        chatbot_config_service = ChatbotConfigService()
        palabras = chatbot_config_service.get_historial_palabras_riesgo()
        return JsonResponse({"success": True, "palabras": palabras}, status=200)
